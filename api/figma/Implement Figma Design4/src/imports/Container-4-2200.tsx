import svgPaths from "./svg-yqvxem51n2";

function MeatballsMenu() {
  return (
    <div className="absolute contents inset-[45.83%_20.83%_45.83%_45.83%]" data-name="Meatballs_menu">
      <div className="absolute inset-[45.83%]">
        <div className="absolute inset-[-50%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 4">
            <path d={svgPaths.p32cd9cf0} id="Ellipse 206" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeWidth="2" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[45.83%_20.83%_45.83%_70.83%]">
        <div className="absolute inset-[-50%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 4">
            <path d={svgPaths.p32cd9cf0} id="Ellipse 206" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeWidth="2" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Icon() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <MeatballsMenu />
    </div>
  );
}

function Container2() {
  return (
    <div className="content-stretch flex flex-col items-start relative size-[24px]" data-name="Container">
      <Icon />
    </div>
  );
}

function MeatballsMenu1() {
  return (
    <div className="absolute contents inset-[45.83%_20.83%_45.83%_45.83%]" data-name="Meatballs_menu">
      <div className="absolute inset-[45.83%]">
        <div className="absolute inset-[-50%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 4">
            <path d={svgPaths.p32cd9cf0} id="Ellipse 206" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeWidth="2" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[45.83%_20.83%_45.83%_70.83%]">
        <div className="absolute inset-[-50%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 4">
            <path d={svgPaths.p32cd9cf0} id="Ellipse 206" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeWidth="2" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Icon1() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <MeatballsMenu1 />
    </div>
  );
}

function Container3() {
  return (
    <div className="content-stretch flex flex-col items-start relative size-[24px]" data-name="Container">
      <Icon1 />
    </div>
  );
}

function Container1() {
  return (
    <div className="h-[54px] relative w-[24px]" data-name="Container">
      <div className="absolute flex items-center justify-center left-px size-[24px] top-[25px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "36" } as React.CSSProperties}>
        <div className="-rotate-90 flex-none">
          <Container2 />
        </div>
      </div>
      <div className="absolute flex items-center justify-center left-px size-[24px] top-[13px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "36" } as React.CSSProperties}>
        <div className="-rotate-90 flex-none">
          <Container3 />
        </div>
      </div>
    </div>
  );
}

export default function Container() {
  return (
    <div className="content-stretch flex items-center justify-center px-[8px] py-[3px] relative size-full" data-name="Container">
      <div className="flex items-center justify-center relative shrink-0">
        <div className="flex-none rotate-180">
          <Container1 />
        </div>
      </div>
    </div>
  );
}