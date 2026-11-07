import type { Metadata } from "next";
import { HataSahnesi } from "@/components/HataSahnesi";
import { ButonLink } from "@/components/ui/ButonLink";

// `noindex` meta'sını Next.js 404 yanıtlarına kendisi ekler.
export const metadata: Metadata = {
  title: "Sayfa bulunamadı",
};

export default function NotFound() {
  return (
    <HataSahnesi
      kod="404"
      baslik="Aradığınız sayfa bulunamadı"
      aciklama="Sayfa taşınmış, kaldırılmış ya da adres yanlış yazılmış olabilir. Aşağıdaki bağlantılarla devam edebilirsiniz."
    >
      <ButonLink href="/" stil="birincil">
        Anasayfaya dön
      </ButonLink>
      <ButonLink href="/blog" stil="ikincil">
        Blog
      </ButonLink>
      <ButonLink href="/iletisim" stil="hayalet">
        İletişim
      </ButonLink>
    </HataSahnesi>
  );
}
