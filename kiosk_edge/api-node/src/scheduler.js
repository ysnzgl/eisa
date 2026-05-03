// Push/Pull mantığı — node-cron tabanlı.
// PULL: kategoriler/sorular + kampanyaları merkezden çekip SQLite'a upsert eder.
// PUSH: outbox'taki anonim logları merkeze iter ve pushed_at damgası vurur.
import cron from 'node-cron';
import { Agent, fetch } from 'undici';

let _tasks = [];
let _undiciAgent = null;

function getAgent(verifyTls) {
  if (_undiciAgent) return _undiciAgent;
  _undiciAgent = new Agent({
    connect: { rejectUnauthorized: !!verifyTls },
  });
  return _undiciAgent;
}

function authHeaders(settings) {
  return {
    Authorization: `AppKey ${settings.kioskAppKey}`,
    'X-Kiosk-MAC': settings.kioskMac,
  };
}

async function request(settings, method, pathPart, body) {
  const url = settings.centralApiBase.replace(/\/+$/, '') + pathPart;
  const headers = authHeaders(settings);
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    dispatcher: getAgent(settings.verifyTls),
    signal: AbortSignal.timeout(15000),
  });
  return res;
}

function upsertCategory(db, c) {
  const exists = db.prepare('SELECT id FROM categories WHERE id = ?').get(c.id);
  if (exists) {
    db.prepare(
      `UPDATE categories SET slug=@slug, name=@name, is_sensitive=@is_sensitive, is_active=@is_active WHERE id=@id`,
    ).run({
      id: c.id,
      slug: c.slug,
      name: c.name,
      is_sensitive: c.is_sensitive ? 1 : 0,
      is_active: c.is_active === false ? 0 : 1,
    });
  } else {
    db.prepare(
      `INSERT INTO categories (id, slug, name, icon, is_sensitive, is_active)
       VALUES (@id, @slug, @name, @icon, @is_sensitive, @is_active)`,
    ).run({
      id: c.id,
      slug: c.slug,
      name: c.name,
      icon: c.icon || 'fa-circle',
      is_sensitive: c.is_sensitive ? 1 : 0,
      is_active: c.is_active === false ? 0 : 1,
    });
  }
}

function upsertQuestion(db, q, categoryId) {
  const exists = db.prepare('SELECT id FROM questions WHERE id = ?').get(q.id);
  if (exists) {
    db.prepare(
      `UPDATE questions SET text=@text, priority=@priority WHERE id=@id`,
    ).run({ id: q.id, text: q.text, priority: q.order ?? q.priority ?? 0 });
  } else {
    db.prepare(
      `INSERT INTO questions (id, category_id, seed_id, text, priority, match_rules)
       VALUES (@id, @category_id, @seed_id, @text, @priority, @match_rules)`,
    ).run({
      id: q.id,
      category_id: categoryId,
      seed_id: q.seed_id || `q_${q.id}`,
      text: q.text,
      priority: q.order ?? q.priority ?? 0,
      match_rules: JSON.stringify(q.match_rules ?? []),
    });
  }
}

function upsertCampaign(db, c) {
  const targeting = {
    cities: c.target_cities ?? [],
    districts: c.target_districts ?? [],
    age_ranges: c.target_age_ranges ?? [],
    genders: c.target_genders ?? [],
  };
  const exists = db.prepare('SELECT id FROM campaigns WHERE id = ?').get(c.id);
  const params = {
    id: c.id,
    name: c.name,
    media_local_path: c.media_url || '',
    starts_at: c.starts_at,
    ends_at: c.ends_at,
    targeting: JSON.stringify(targeting),
    is_active: c.is_active === false ? 0 : 1,
  };
  if (exists) {
    db.prepare(
      `UPDATE campaigns SET name=@name, media_local_path=@media_local_path,
       starts_at=@starts_at, ends_at=@ends_at, targeting=@targeting, is_active=@is_active
       WHERE id=@id`,
    ).run(params);
  } else {
    db.prepare(
      `INSERT INTO campaigns (id, name, media_local_path, starts_at, ends_at, targeting, is_active)
       VALUES (@id, @name, @media_local_path, @starts_at, @ends_at, @targeting, @is_active)`,
    ).run(params);
  }
}

export async function pullFromCentral(db, settings, log = console) {
  try {
    // 1) products/sync — kategoriler + sorular
    const r1 = await request(settings, 'GET', '/api/products/sync/');
    if (r1.ok) {
      const data = await r1.json();
      const tx = db.transaction((cats) => {
        for (const cat of cats) {
          upsertCategory(db, cat);
          for (const q of cat.questions || []) {
            upsertQuestion(db, q, cat.id);
          }
        }
      });
      tx(data.categories || []);
      log.info?.(`PULL: ${(data.categories || []).length} kategori güncellendi`);
    } else {
      log.warn?.(`PULL products/sync HTTP ${r1.status}`);
    }

    // 2) campaigns/sync
    const r2 = await request(settings, 'GET', '/api/campaigns/sync/');
    if (r2.ok) {
      const camps = await r2.json();
      const tx = db.transaction((items) => {
        for (const c of items) upsertCampaign(db, c);
      });
      tx(camps);
      log.info?.(`PULL: ${camps.length} kampanya güncellendi`);
    } else {
      log.warn?.(`PULL campaigns/sync HTTP ${r2.status}`);
    }
  } catch (err) {
    log.error?.({ err }, 'PULL başarısız (offline mod)');
  }
}

export async function pushToCentral(db, settings, log = console) {
  try {
    // 1) session_log_outbox — "Forward & Drop":
    //    Merkez 200/201 dönerse satır LOKAL SQLITE'TAN KESİNLİKLE SİLİNİR.
    //    Böylece offline-first kuyruk merkezde gerçeklik haline gelir gelmez yer açılır.
    const sessions = db
      .prepare(
        'SELECT id, payload FROM session_log_outbox WHERE pushed_at IS NULL LIMIT 50',
      )
      .all();
    if (sessions.length) {
      const r = await request(settings, 'POST', '/api/analytics/sessions/', {
        items: sessions.map((s) => JSON.parse(s.payload)),
      });
      if (r.ok || r.status === 201) {
        const del = db.prepare('DELETE FROM session_log_outbox WHERE id = ?');
        const tx = db.transaction((rows) => {
          for (const row of rows) del.run(row.id);
        });
        tx(sessions);
        log.info?.(
          `PUSH: ${sessions.length} oturum logu gönderildi ve lokalden silindi`,
        );
      } else {
        log.warn?.(`PUSH sessions HTTP ${r.status}`);
      }
    }

    // 2) ad_impression_outbox — aynı Forward & Drop politikası.
    const imps = db
      .prepare(
        'SELECT id, payload FROM ad_impression_outbox WHERE pushed_at IS NULL LIMIT 100',
      )
      .all();
    if (imps.length) {
      const r = await request(settings, 'POST', '/api/analytics/impressions/', {
        items: imps.map((i) => JSON.parse(i.payload)),
      });
      if (r.ok || r.status === 201) {
        const del = db.prepare('DELETE FROM ad_impression_outbox WHERE id = ?');
        const tx = db.transaction((rows) => {
          for (const row of rows) del.run(row.id);
        });
        tx(imps);
        log.info?.(
          `PUSH: ${imps.length} impression logu gönderildi ve lokalden silindi`,
        );
      } else {
        log.warn?.(`PUSH impressions HTTP ${r.status}`);
      }
    }
  } catch (err) {
    log.error?.({ err }, 'PUSH başarısız (offline mod)');
  }
}

export function startScheduler(db, settings, log = console) {
  if (_tasks.length) return;
  // node-cron en küçük birimi 1 dakikadır; saniye bazlı interval için setInterval kullanıyoruz.
  const pullEvery = settings.pullIntervalSec * 1000;
  const pushEvery = settings.pushIntervalSec * 1000;

  const pullTimer = setInterval(() => {
    pullFromCentral(db, settings, log);
  }, pullEvery);
  const pushTimer = setInterval(() => {
    pushToCentral(db, settings, log);
  }, pushEvery);
  // Node event loop'unu canlı tutmasın
  pullTimer.unref?.();
  pushTimer.unref?.();
  _tasks.push(pullTimer, pushTimer);

  log.info?.(
    `Scheduler başlatıldı — pull:${settings.pullIntervalSec}s push:${settings.pushIntervalSec}s`,
  );
}

export function stopScheduler() {
  for (const t of _tasks) clearInterval(t);
  _tasks = [];
}

// node-cron kullanımı isteğe bağlı (ileride saatlik full sync vb.)
export { cron };
