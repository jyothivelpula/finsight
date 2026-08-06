type BrandLogoProps = {
  className?: string;
  imgClassName?: string;
};

export default function BrandLogo({
  className = "",
  imgClassName = "h-9 w-auto",
}: BrandLogoProps) {
  return (
    <div className={`inline-flex items-center ${className}`}>
      <img
        src="/finsight-logo.png"
        alt="FinSight"
        className={`object-contain object-left ${imgClassName}`}
      />
    </div>
  );
}
