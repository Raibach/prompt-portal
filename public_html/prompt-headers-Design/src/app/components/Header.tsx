import svgPaths from "../../imports/svg-tlqdb8g9ws";
import imgEdison from "figma:asset/1cceea09534772c1da677699f6766a61109c457c.png";

interface HeaderProps {
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

export default function Header({ activeTab = 'composer', onTabChange }: HeaderProps) {
  const tabs = [
    { id: 'console', label: 'Console', icon: 'console' },
    { id: 'composer', label: 'Composer', icon: 'composer' },
    { id: 'evaluation', label: 'Evaluation', icon: 'evaluation' },
    { id: 'variables', label: 'Variables', icon: 'variables' },
    { id: 'metadata', label: 'Metadata', icon: 'metadata' },
  ];

  return (
    <div className="content-stretch flex flex-col items-center justify-end relative w-full h-[73px]">
      <div className="content-stretch flex gap-[21px] h-[73px] items-center relative shrink-0 w-full" style={{ backgroundImage: "linear-gradient(-90deg, rgb(240, 179, 35) 0%, rgb(254, 209, 65) 49.459%, rgb(254, 209, 65) 99.918%)" }}>
        {/* Edison Logo */}
        <div className="h-[72px] relative shrink-0 w-[187px]">
          <div className="absolute h-[72px] left-[8px] top-[0.5px] w-[179px]">
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
              <img alt="Edison" className="absolute h-[141.98%] left-[-43.52%] max-w-none top-0 w-[143.75%]" src={imgEdison} />
            </div>
          </div>
        </div>

        <div className="bg-[rgba(217,217,217,0)] flex-[1_0_0] h-[76px] min-h-px min-w-px" />

        {/* Navigation Tabs */}
        <div className="content-stretch flex gap-[16px] h-[76px] items-center px-[30px] relative shrink-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange?.(tab.id)}
              className="content-stretch flex gap-[4px] h-[70px] items-center py-[4px] relative shrink-0 hover:opacity-80 transition-opacity"
            >
              {/* Tab Icon */}
              {tab.icon === 'console' && (
                <div className="h-[21.778px] relative w-[21.312px]">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.3124 21.7778">
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.77603" stroke="#155258" strokeWidth="1.2" transform="rotate(90 15.9843 8.16667)" width="3.62963" x="15.9843" y="8.16667" />
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.77603" stroke="#155258" strokeWidth="1.2" transform="rotate(90 15.9843 15.4259)" width="3.62963" x="15.9843" y="15.4259" />
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.77603" stroke="#155258" strokeWidth="1.2" transform="rotate(-90 2.66405 6.35185)" width="3.62963" x="2.66405" y="6.35185" />
                    <path d={svgPaths.pa05f480} stroke="#155258" strokeWidth="1.2" />
                    <path d={svgPaths.p12182880} stroke="#155258" strokeWidth="1.2" />
                  </svg>
                </div>
              )}
              
              {tab.icon === 'composer' && (
                <div className="h-[21px] relative w-[21.312px]">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.3124 21">
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.75" stroke={activeTab === 'composer' ? '#4066E3' : '#155258'} strokeWidth="1.2" transform="rotate(90 15.9843 7.875)" width="3.5" x="15.9843" y="7.875" />
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.75" stroke={activeTab === 'composer' ? '#4066E3' : '#155258'} strokeWidth="1.2" transform="rotate(90 15.9843 14.875)" width="3.5" x="15.9843" y="14.875" />
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.75" stroke={activeTab === 'composer' ? '#4066E3' : '#155258'} strokeWidth="1.2" transform="rotate(-90 2.66405 6.125)" width="3.5" x="2.66405" y="6.125" />
                    <path d={svgPaths.p328c9160} stroke={activeTab === 'composer' ? '#4066E3' : '#155258'} strokeWidth="1.2" />
                    <path d={svgPaths.p170ebbc0} stroke={activeTab === 'composer' ? '#4066E3' : '#155258'} strokeWidth="1.2" />
                  </svg>
                </div>
              )}

              {tab.icon === 'evaluation' && (
                <div className="size-[21px] relative">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21 21">
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.5" rx="1.75" stroke="#2A2836" strokeWidth="1.2" transform="rotate(90 15.75 7.875)" width="3.5" x="15.75" y="7.875" />
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.5" rx="1.75" stroke="#2A2836" strokeWidth="1.2" transform="rotate(90 15.75 14.875)" width="3.5" x="15.75" y="14.875" />
                    <rect fill="#7E869E" fillOpacity="0.25" height="3.5" rx="1.75" stroke="#2A2836" strokeWidth="1.2" transform="rotate(-90 2.625 6.125)" width="3.5" x="2.625" y="6.125" />
                    <path d={svgPaths.p23a5f900} stroke="#2A2836" strokeWidth="1.2" />
                    <path d={svgPaths.p1be78c00} stroke="#2A2836" strokeWidth="1.2" />
                  </svg>
                </div>
              )}

              {tab.icon === 'variables' && (
                <div className="relative shrink-0 size-[19px]">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19 19">
                    <path d={svgPaths.p1fe03340} stroke="#155258" />
                    <path d={svgPaths.p137b6870} stroke="#155258" />
                    <path d={svgPaths.p1e42fb00} stroke="#155258" />
                  </svg>
                </div>
              )}

              {tab.icon === 'metadata' && (
                <div className="relative shrink-0 size-[22px]">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22 22">
                    <path d={svgPaths.p68ff600} fill="#7E869E" fillOpacity="0.25" stroke="#155258" />
                    <ellipse cx="11" cy="6.41667" rx="6.41667" ry="2.75" stroke="#155258" strokeWidth="1.2" />
                    <path d={svgPaths.p2ddb2d00} stroke="#155258" strokeLinecap="square" strokeWidth="1.2" />
                    <path d={svgPaths.p1e08bb80} stroke="#155258" strokeWidth="1.2" />
                  </svg>
                </div>
              )}

              {/* Tab Label */}
              <p 
                className={`font-['Inter:Semi_Bold',sans-serif] font-semibold leading-[normal] not-italic relative shrink-0 text-[16px] w-[98.443px] whitespace-pre-wrap ${
                  activeTab === tab.id ? 'text-[#4066e3]' : 'text-[#155258]'
                }`}
              >
                {tab.label}
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
