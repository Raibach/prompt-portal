import svgPaths from "./svg-h90mn5y3f8";
import imgImage from "figma:asset/a0c698671eb795bc84024e87ad7c0b231c53115c.png";
import { imgVector } from "./svg-d944n";

function Image() {
  return (
    <div className="h-[65.984px] relative shrink-0 w-full" data-name="Image">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage} />
    </div>
  );
}

function Container() {
  return (
    <div className="content-stretch flex flex-col h-[66px] items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <Image />
    </div>
  );
}

function MachineLearningModel() {
  return (
    <div className="absolute contents inset-0" data-name="Machine-learning-model">
      <div className="absolute inset-0 mix-blend-multiply" data-name="Vector">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 26 25">
          <g id="Vector" style={{ mixBlendMode: "multiply" }}>
            <path d="M26 0H0V25H26V0Z" fill="var(--fill-0, white)" fillOpacity="0.01" />
          </g>
        </svg>
      </div>
      <div className="absolute inset-[6.25%]" data-name="Vector">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22.75 21.8752">
          <path d={svgPaths.pd073400} fill="var(--fill-0, #507274)" id="Vector" />
        </svg>
      </div>
    </div>
  );
}

function Icon() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <MachineLearningModel />
    </div>
  );
}

function Container2() {
  return (
    <div className="absolute content-stretch flex flex-col h-[25px] items-start left-[22px] top-[13px] w-[26px]" data-name="Container">
      <Icon />
    </div>
  );
}

function Paragraph() {
  return (
    <div className="h-[20px] relative shrink-0 w-[47px]" data-name="Paragraph">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Bold',sans-serif] font-bold leading-[20px] left-[23.98px] not-italic text-[#507274] text-[13px] text-center top-0">Trace</p>
      </div>
    </div>
  );
}

function Container3() {
  return (
    <div className="absolute content-stretch flex flex-col h-[16px] items-start justify-center left-[14px] top-[48px] w-[47px]" data-name="Container">
      <Paragraph />
    </div>
  );
}

function Container1() {
  return (
    <div className="bg-[#fccd3d] h-[77px] relative shrink-0 w-full" data-name="Container">
      <Container2 />
      <Container3 />
    </div>
  );
}

function Group() {
  return (
    <div className="absolute contents inset-[0_16.23%_15.63%_16.97%]">
      <div className="absolute inset-[0_16.23%_15.63%_16.97%]" data-name="Vector">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24.7178 19.7878">
          <path d={svgPaths.p2723500} fill="var(--fill-0, #4ECFD5)" id="Vector" />
        </svg>
      </div>
    </div>
  );
}

function Icon1() {
  return (
    <div className="h-[23.453px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <Group />
    </div>
  );
}

function Container5() {
  return (
    <div className="absolute content-stretch flex flex-col h-[23.453px] items-start left-[11px] top-px w-[37px]" data-name="Container">
      <Icon1 />
    </div>
  );
}

function Paragraph1() {
  return (
    <div className="h-[20px] relative shrink-0 w-[60px]" data-name="Paragraph">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[20px] left-[29.7px] not-italic text-[#4ecfd5] text-[13px] text-center top-0">Variables</p>
      </div>
    </div>
  );
}

function Container6() {
  return (
    <div className="absolute content-stretch flex flex-col h-[16px] items-start justify-center left-0 top-[31px] w-[60px]" data-name="Container">
      <Paragraph1 />
    </div>
  );
}

function Frame() {
  return (
    <div className="absolute h-[47px] left-[7.42px] top-[10px] w-[60px]">
      <Container5 />
      <Container6 />
    </div>
  );
}

function Container4() {
  return (
    <div className="h-[67px] relative shrink-0 w-full" data-name="Container">
      <Frame />
    </div>
  );
}

function ModelFoundation() {
  return (
    <div className="absolute contents inset-0" data-name="Model--foundation">
      <div className="absolute inset-0 mix-blend-multiply" data-name="Vector">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 25 23">
          <g id="Vector" style={{ mixBlendMode: "multiply" }}>
            <path d="M25 0H0V23H25V0Z" fill="var(--fill-0, white)" fillOpacity="0.01" />
          </g>
        </svg>
      </div>
      <div className="absolute inset-[6.25%]" data-name="Vector">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.8752 20.125">
          <path d={svgPaths.p2442da00} fill="var(--fill-0, #4ECFD5)" id="Vector" />
        </svg>
      </div>
    </div>
  );
}

function Icon2() {
  return (
    <div className="h-[23px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <ModelFoundation />
    </div>
  );
}

function Container8() {
  return (
    <div className="absolute content-stretch flex flex-col h-[23px] items-start left-[17px] top-px w-[25px]" data-name="Container">
      <Icon2 />
    </div>
  );
}

function Paragraph2() {
  return (
    <div className="h-[20px] relative shrink-0 w-[60px]" data-name="Paragraph">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[20px] left-[29.7px] not-italic text-[#4ecfd5] text-[13px] text-center top-0">Tools</p>
      </div>
    </div>
  );
}

function Container9() {
  return (
    <div className="absolute content-stretch flex flex-col h-[16px] items-start justify-center left-0 top-[31px] w-[60px]" data-name="Container">
      <Paragraph2 />
    </div>
  );
}

function Frame1() {
  return (
    <div className="absolute h-[47px] left-[7.42px] top-[10px] w-[60px]">
      <Container8 />
      <Container9 />
    </div>
  );
}

function Container7() {
  return (
    <div className="h-[67px] relative shrink-0 w-full" data-name="Container">
      <Frame1 />
    </div>
  );
}

function Vector() {
  return (
    <div className="absolute contents inset-[3.13%_3.12%_3.13%_3.13%]" data-name="Vector">
      <div className="absolute inset-[34.38%_34.38%_28.13%_34.38%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-9.625px_-9.281px] mask-size-[28px_27px]" data-name="Vector" style={{ maskImage: `url('${imgVector}')` }}>
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.75 10.125">
          <path d={svgPaths.p37a9d580} fill="var(--fill-0, #4ECFD5)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[43.75%_61.54%_8.36%_3.13%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-0.875px_-11.813px] mask-size-[28px_27px]" data-name="Vector" style={{ maskImage: `url('${imgVector}')` }}>
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.8939 12.9302">
          <path d={svgPaths.p28523180} fill="var(--fill-0, #4ECFD5)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[61.54%_8.36%_3.13%_43.75%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-12.25px_-16.615px] mask-size-[28px_27px]" data-name="Vector" style={{ maskImage: `url('${imgVector}')` }}>
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.409 9.5407">
          <path d={svgPaths.p38fec300} fill="var(--fill-0, #4ECFD5)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[8.36%_3.12%_43.75%_61.54%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-17.231px_-2.257px] mask-size-[28px_27px]" data-name="Vector" style={{ maskImage: `url('${imgVector}')` }}>
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.8939 12.9301">
          <path d={svgPaths.pf757880} fill="var(--fill-0, #4ECFD5)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[3.13%_43.75%_61.54%_8.36%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-2.341px_-0.844px] mask-size-[28px_27px]" data-name="Vector" style={{ maskImage: `url('${imgVector}')` }}>
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.409 9.54075">
          <path d={svgPaths.p38511e00} fill="var(--fill-0, #4ECFD5)" id="Vector" />
        </svg>
      </div>
    </div>
  );
}

function AiGovernanceLifecycle() {
  return (
    <div className="absolute contents inset-0" data-name="AI-governance--lifecycle">
      <div className="absolute inset-0 mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[0px_0px] mask-size-[28px_27px] mix-blend-multiply" data-name="Vector" style={{ maskImage: `url('${imgVector}')` }}>
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 28 27">
          <g id="Vector" style={{ mixBlendMode: "multiply" }}>
            <path d="M28 0H0V27H28V0Z" fill="var(--fill-0, white)" fillOpacity="0.01" />
          </g>
        </svg>
      </div>
      <Vector />
    </div>
  );
}

function ClipPathGroup() {
  return (
    <div className="absolute contents inset-0" data-name="Clip path group">
      <AiGovernanceLifecycle />
    </div>
  );
}

function Icon3() {
  return (
    <div className="h-[27px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <ClipPathGroup />
    </div>
  );
}

function Container11() {
  return (
    <div className="absolute content-stretch flex flex-col h-[27px] items-start left-[15px] top-0 w-[28px]" data-name="Container">
      <Icon3 />
    </div>
  );
}

function Paragraph3() {
  return (
    <div className="h-[20px] relative shrink-0 w-[60px]" data-name="Paragraph">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[20px] left-[29.7px] not-italic text-[#4ecfd5] text-[13px] text-center top-0">Data</p>
      </div>
    </div>
  );
}

function Container12() {
  return (
    <div className="absolute content-stretch flex flex-col h-[16px] items-start justify-center left-0 top-[31px] w-[60px]" data-name="Container">
      <Paragraph3 />
    </div>
  );
}

function Frame2() {
  return (
    <div className="absolute h-[47px] left-[7.42px] top-[10px] w-[60px]">
      <Container11 />
      <Container12 />
    </div>
  );
}

function Container10() {
  return (
    <div className="h-[67px] relative shrink-0 w-full" data-name="Container">
      <Frame2 />
    </div>
  );
}

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

function Icon4() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <MeatballsMenu />
    </div>
  );
}

function Container15() {
  return (
    <div className="content-stretch flex flex-col items-start relative size-[24px]" data-name="Container">
      <Icon4 />
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

function Icon5() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <MeatballsMenu1 />
    </div>
  );
}

function Container16() {
  return (
    <div className="content-stretch flex flex-col items-start relative size-[24px]" data-name="Container">
      <Icon5 />
    </div>
  );
}

function Container14() {
  return (
    <div className="h-[54px] relative w-[24px]" data-name="Container">
      <div className="absolute flex items-center justify-center left-px size-[24px] top-[25px]" style={{ "--transform-inner-width": "1185", "--transform-inner-height": "306" } as React.CSSProperties}>
        <div className="-rotate-90 flex-none">
          <Container15 />
        </div>
      </div>
      <div className="absolute flex items-center justify-center left-px size-[24px] top-[13px]" style={{ "--transform-inner-width": "1185", "--transform-inner-height": "306" } as React.CSSProperties}>
        <div className="-rotate-90 flex-none">
          <Container16 />
        </div>
      </div>
    </div>
  );
}

function Container13() {
  return (
    <div className="relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-row items-center justify-center size-full">
        <div className="content-stretch flex items-center justify-center px-[8px] py-[3px] relative w-full">
          <div className="flex items-center justify-center relative shrink-0">
            <div className="flex-none rotate-180">
              <Container14 />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Frame3() {
  return (
    <div className="content-stretch flex flex-col gap-[5px] items-start relative size-full">
      <Container />
      <Container1 />
      <Container4 />
      <Container7 />
      <Container10 />
      <Container13 />
    </div>
  );
}