export function LogoSection() {
  return (
    <div className="flex items-center gap-3 absolute left-1/2 transform -translate-x-1/2">
      {/* Prism Logo */}
      <img
        src="/prismadv-logo.png"
        alt="PrismaDV"
        className="h-7 w-auto flex-shrink-0 relative top-[3px]"
      />

      {/* Text Logo */}
      <div className="flex items-baseline font-bold text-lg leading-none">
        <span className="text-text-primary">Prisma</span>
        <span className="text-accent-blue">DV</span>
      </div>
    </div>
  );
}
