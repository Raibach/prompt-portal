/**
 * @figmaAssetKey 2c50e8fb2a46d6866bd162d11372bfba1d7bdd73
 */
function Frame1({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div aria-hidden="true" className="absolute border border-[#9162c2] border-solid inset-0 pointer-events-none rounded-[5px]" />
      <div className="flex flex-col font-['Manrope:Regular',sans-serif] font-normal justify-center leading-[0] relative shrink-0 text-[#d4a0ee] text-[14px] text-center text-nowrap">
        <p className="leading-[normal] whitespace-pre">PDF Summarizer</p>
      </div>
    </div>
  );
}

function Frame3() {
  return (
    <div className="box-border content-stretch flex gap-[10px] h-[32px] items-center justify-center p-[5px] relative rounded-[5px] shrink-0 w-[99px]">
      <div aria-hidden="true" className="absolute border border-[#9162c2] border-solid inset-0 pointer-events-none rounded-[5px]" />
      <div className="flex flex-col font-['Manrope:Bold',sans-serif] font-bold h-[19.009px] justify-center leading-[0] relative shrink-0 text-[14px] text-center text-white w-[63px]">
        <p className="leading-[normal]">My Story</p>
      </div>
    </div>
  );
}

function Component() {
  return (
    <div className="box-border content-stretch flex gap-[10px] h-[32px] items-center justify-center px-[10px] py-[5px] relative rounded-[5px] shrink-0 w-[134px]">
      <div aria-hidden="true" className="absolute border border-[#9162c2] border-solid inset-0 pointer-events-none rounded-[5px]" />
      <div className="flex flex-col font-['Manrope:Regular',sans-serif] font-normal justify-center leading-[0] relative shrink-0 text-[#d4a0ee] text-[14px] text-center text-nowrap">
        <p className="leading-[normal] whitespace-pre">Quarantine [20]</p>
      </div>
    </div>
  );
}

function Component1() {
  return (
    <div className="box-border content-stretch flex gap-[10px] h-[32px] items-center justify-center px-[10px] py-[5px] relative rounded-[5px] shrink-0 w-[118px]">
      <div aria-hidden="true" className="absolute border border-[#9162c2] border-solid inset-0 pointer-events-none rounded-[5px]" />
      <div className="flex flex-col font-['Manrope:Regular',sans-serif] font-normal justify-center leading-[0] relative shrink-0 text-[#d4a0ee] text-[14px] text-center text-nowrap">
        <p className="leading-[normal] whitespace-pre">Memory Recall</p>
      </div>
    </div>
  );
}

function Component2() {
  return (
    <div className="box-border content-stretch flex gap-[10px] h-[32px] items-center justify-center px-[10px] py-[5px] relative rounded-[5px] shrink-0 w-[125px]">
      <div aria-hidden="true" className="absolute border border-[#9162c2] border-solid inset-0 pointer-events-none rounded-[5px]" />
      <div className="flex flex-col font-['Manrope:Regular',sans-serif] font-normal justify-center leading-[0] relative shrink-0 text-[#d4a0ee] text-[14px] text-center text-nowrap">
        <p className="leading-[normal] whitespace-pre">Reasoning Trail</p>
      </div>
    </div>
  );
}

function Component3() {
  return (
    <div className="box-border content-stretch flex gap-[10px] h-[32px] items-center justify-center px-[10px] py-[5px] relative rounded-[5px] shrink-0 w-[101px]">
      <div aria-hidden="true" className="absolute border border-[#9162c2] border-solid inset-0 pointer-events-none rounded-[5px]" />
      <div className="flex flex-col font-['Manrope:Regular',sans-serif] font-normal justify-center leading-[0] relative shrink-0 text-[#d4a0ee] text-[14px] text-center text-nowrap">
        <p className="leading-[normal] whitespace-pre">Cloud Sync</p>
      </div>
    </div>
  );
}

function Frame2() {
  return (
    <div className="content-stretch flex gap-[10px] items-center relative shrink-0 w-full">
      <div className="relative shrink-0 size-[41.304px]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 42 42">
          <circle cx="20.652" cy="20.652" fill="var(--fill-0, #D9D9D9)" id="Ellipse 1" r="20.652" />
        </svg>
      </div>
      <Frame3 />
      <Frame1 className="box-border content-stretch flex gap-[10px] h-[32px] items-center justify-center px-[10px] py-[5px] relative rounded-[5px] shrink-0 w-[123px]" />
      <Component />
      <Component1 />
      <Component2 />
      <Component3 />
    </div>
  );
}

export default function Frame() {
  return (
    <div className="relative rounded-tl-[10px] rounded-tr-[10px] size-full">
      <div className="flex flex-col justify-center size-full">
        <div className="box-border content-stretch flex flex-col items-start justify-center p-[10px] relative size-full">
          <Frame2 />
        </div>
      </div>
    </div>
  );
}