/**
 * İkon — CONTRACT §2'deki 48 Phosphor ikonunun haritası.
 *
 * - Her ikon TEK TEK import edilir (barrel import yok) ve SSR sürümü kullanılır
 *   (`@phosphor-icons/react/dist/ssr/*`): server component'lerde sıfır istemci JS'i.
 * - Bilinmeyen ad → `Sparkle`.
 * - Varsayılan `weight="duotone"`, dekoratif (`aria-hidden`). Anlam taşıyorsa `etiket` verin.
 *
 * Not: Bu dosya bir client component içinden import edilirse 48 ikonun tamamı istemci
 * paketine girer. Client adacıklarında ikon gerekiyorsa sunucudan `<Icon />` elementini
 * prop/children olarak geçirmeyi tercih edin.
 */

import type { Icon as PhosphorIkon, IconWeight } from "@phosphor-icons/react";
import { SparkleIcon } from "@phosphor-icons/react/dist/ssr/Sparkle";
import { BrainIcon } from "@phosphor-icons/react/dist/ssr/Brain";
import { ShieldCheckIcon } from "@phosphor-icons/react/dist/ssr/ShieldCheck";
import { PackageIcon } from "@phosphor-icons/react/dist/ssr/Package";
import { ClockCounterClockwiseIcon } from "@phosphor-icons/react/dist/ssr/ClockCounterClockwise";
import { TimerIcon } from "@phosphor-icons/react/dist/ssr/Timer";
import { CheckCircleIcon } from "@phosphor-icons/react/dist/ssr/CheckCircle";
import { UserCircleIcon } from "@phosphor-icons/react/dist/ssr/UserCircle";
import { UsersIcon } from "@phosphor-icons/react/dist/ssr/Users";
import { StorefrontIcon } from "@phosphor-icons/react/dist/ssr/Storefront";
import { QrCodeIcon } from "@phosphor-icons/react/dist/ssr/QrCode";
import { ReceiptIcon } from "@phosphor-icons/react/dist/ssr/Receipt";
import { ChartLineUpIcon } from "@phosphor-icons/react/dist/ssr/ChartLineUp";
import { TrendUpIcon } from "@phosphor-icons/react/dist/ssr/TrendUp";
import { CoinsIcon } from "@phosphor-icons/react/dist/ssr/Coins";
import { CurrencyCircleDollarIcon } from "@phosphor-icons/react/dist/ssr/CurrencyCircleDollar";
import { DevicesIcon } from "@phosphor-icons/react/dist/ssr/Devices";
import { DeviceMobileIcon } from "@phosphor-icons/react/dist/ssr/DeviceMobile";
import { MonitorIcon } from "@phosphor-icons/react/dist/ssr/Monitor";
import { CloudIcon } from "@phosphor-icons/react/dist/ssr/Cloud";
import { CloudArrowUpIcon } from "@phosphor-icons/react/dist/ssr/CloudArrowUp";
import { WifiSlashIcon } from "@phosphor-icons/react/dist/ssr/WifiSlash";
import { LightningIcon } from "@phosphor-icons/react/dist/ssr/Lightning";
import { HeartIcon } from "@phosphor-icons/react/dist/ssr/Heart";
import { HeartbeatIcon } from "@phosphor-icons/react/dist/ssr/Heartbeat";
import { FirstAidKitIcon } from "@phosphor-icons/react/dist/ssr/FirstAidKit";
import { PillIcon } from "@phosphor-icons/react/dist/ssr/Pill";
import { FlaskIcon } from "@phosphor-icons/react/dist/ssr/Flask";
import { LeafIcon } from "@phosphor-icons/react/dist/ssr/Leaf";
import { MoonIcon } from "@phosphor-icons/react/dist/ssr/Moon";
import { LockIcon } from "@phosphor-icons/react/dist/ssr/Lock";
import { HandshakeIcon } from "@phosphor-icons/react/dist/ssr/Handshake";
import { TargetIcon } from "@phosphor-icons/react/dist/ssr/Target";
import { MegaphoneIcon } from "@phosphor-icons/react/dist/ssr/Megaphone";
import { LightbulbIcon } from "@phosphor-icons/react/dist/ssr/Lightbulb";
import { RocketIcon } from "@phosphor-icons/react/dist/ssr/Rocket";
import { GearIcon } from "@phosphor-icons/react/dist/ssr/Gear";
import { CpuIcon } from "@phosphor-icons/react/dist/ssr/Cpu";
import { EyeIcon } from "@phosphor-icons/react/dist/ssr/Eye";
import { ChatCircleTextIcon } from "@phosphor-icons/react/dist/ssr/ChatCircleText";
import { EnvelopeIcon } from "@phosphor-icons/react/dist/ssr/Envelope";
import { PhoneIcon } from "@phosphor-icons/react/dist/ssr/Phone";
import { MapPinIcon } from "@phosphor-icons/react/dist/ssr/MapPin";
import { StarIcon } from "@phosphor-icons/react/dist/ssr/Star";
import { MedalIcon } from "@phosphor-icons/react/dist/ssr/Medal";
import { ArrowsClockwiseIcon } from "@phosphor-icons/react/dist/ssr/ArrowsClockwise";
import { PlantIcon } from "@phosphor-icons/react/dist/ssr/Plant";
import { SmileyIcon } from "@phosphor-icons/react/dist/ssr/Smiley";
import type { IkonAdi } from "@/lib/types";

/** Ad → bileşen. Anahtar kümesi CONTRACT §2 ile birebir (tip sistemi eksik/fazla anahtarı yakalar). */
export const IKONLAR: Record<IkonAdi, PhosphorIkon> = {
  Sparkle: SparkleIcon,
  Brain: BrainIcon,
  ShieldCheck: ShieldCheckIcon,
  Package: PackageIcon,
  ClockCounterClockwise: ClockCounterClockwiseIcon,
  Timer: TimerIcon,
  CheckCircle: CheckCircleIcon,
  UserCircle: UserCircleIcon,
  Users: UsersIcon,
  Storefront: StorefrontIcon,
  QrCode: QrCodeIcon,
  Receipt: ReceiptIcon,
  ChartLineUp: ChartLineUpIcon,
  TrendUp: TrendUpIcon,
  Coins: CoinsIcon,
  CurrencyCircleDollar: CurrencyCircleDollarIcon,
  Devices: DevicesIcon,
  DeviceMobile: DeviceMobileIcon,
  Monitor: MonitorIcon,
  Cloud: CloudIcon,
  CloudArrowUp: CloudArrowUpIcon,
  WifiSlash: WifiSlashIcon,
  Lightning: LightningIcon,
  Heart: HeartIcon,
  Heartbeat: HeartbeatIcon,
  FirstAidKit: FirstAidKitIcon,
  Pill: PillIcon,
  Flask: FlaskIcon,
  Leaf: LeafIcon,
  Moon: MoonIcon,
  Lock: LockIcon,
  Handshake: HandshakeIcon,
  Target: TargetIcon,
  Megaphone: MegaphoneIcon,
  Lightbulb: LightbulbIcon,
  Rocket: RocketIcon,
  Gear: GearIcon,
  Cpu: CpuIcon,
  Eye: EyeIcon,
  ChatCircleText: ChatCircleTextIcon,
  Envelope: EnvelopeIcon,
  Phone: PhoneIcon,
  MapPin: MapPinIcon,
  Star: StarIcon,
  Medal: MedalIcon,
  ArrowsClockwise: ArrowsClockwiseIcon,
  Plant: PlantIcon,
  Smiley: SmileyIcon,
};

export interface IconProps {
  /** CONTRACT §2 ikon adı; bilinmeyen → Sparkle */
  ad: string | null | undefined;
  /** px, varsayılan 24 */
  boyut?: number | string;
  weight?: IconWeight;
  className?: string;
  /** Verilirse ikon anlamlı kabul edilir (role="img" + aria-label). Verilmezse dekoratif. */
  etiket?: string;
}

export function Icon({ ad, boyut = 24, weight = "duotone", className, etiket }: IconProps) {
  const Bilesen = (ad && (IKONLAR as Record<string, PhosphorIkon>)[ad]) || SparkleIcon;
  return (
    <Bilesen
      size={boyut}
      weight={weight}
      className={className}
      aria-hidden={etiket ? undefined : true}
      aria-label={etiket}
      role={etiket ? "img" : undefined}
      focusable="false"
    />
  );
}
