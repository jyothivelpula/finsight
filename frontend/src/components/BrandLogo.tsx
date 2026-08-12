type BrandLogoProps = {
  className?: string;
  imgClassName?: string;
};

export default function BrandLogo({
  className = "",
  imgClassName = "h-9 w-auto",
}: BrandLogoProps) {
  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`} aria-label="FinSight">
      <svg viewBox="0 0 42 42" className={`${imgClassName} aspect-square`} role="img" aria-hidden>
        <defs>
          <linearGradient id="finsight-mark" x1="6" y1="35" x2="36" y2="5" gradientUnits="userSpaceOnUse">
            <stop stopColor="#f06b2c" />
            <stop offset="0.55" stopColor="#e84a57" />
            <stop offset="1" stopColor="#bb38ac" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="38" height="38" rx="12" fill="#25262c" />
        <path d="M11 27.5v-5.2c0-2.1 1.7-3.8 3.8-3.8s3.8 1.7 3.8 3.8v5.2c0 2.1-1.7 3.8-3.8 3.8S11 29.6 11 27.5Z" fill="url(#finsight-mark)" />
        <path d="M19.2 27.5V16.1c0-2.1 1.7-3.8 3.8-3.8s3.8 1.7 3.8 3.8v11.4c0 2.1-1.7 3.8-3.8 3.8s-3.8-1.7-3.8-3.8Z" fill="url(#finsight-mark)" />
        <path d="M27.4 27.5V10.4c0-2.1 1.7-3.8 3.8-3.8s3.8 1.7 3.8 3.8v17.1c0 2.1-1.7 3.8-3.8 3.8s-3.8-1.7-3.8-3.8Z" fill="url(#finsight-mark)" />
        <circle cx="8.4" cy="29.5" r="2.4" fill="#ff8749" />
      </svg>
      <span className="font-display text-lg font-semibold tracking-[-0.06em] text-white">Fin<span className="text-[#ff7d48]">Sight</span></span>
    </div>
  );
}
