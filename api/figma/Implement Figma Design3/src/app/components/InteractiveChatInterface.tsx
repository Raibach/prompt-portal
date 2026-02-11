import { useState, useRef, useEffect } from 'react';
import svgPaths from '../../imports/svg-8sa7r42yg1';
import imgImage from 'figma:asset/a0c698671eb795bc84024e87ad7c0b231c53115c.png';
import { imgVector } from '../../imports/svg-8iauo';
import gripperImage from 'figma:asset/341cef38b0027c50ce380f4f29214f6b82d858b6.png';
import ChatMessage, { ChatMessageData } from './ChatMessage';

export default function InteractiveChatInterface() {
  const [inputHeight, setInputHeight] = useState(180);
  const [isDragging, setIsDragging] = useState(false);
  const startYRef = useRef<number>(0);
  const startHeightRef = useRef<number>(0);
  const [chatInput, setChatInput] = useState('');

  // Example chat messages demonstrating different message types
  const [messages] = useState<ChatMessageData[]>([
    {
      id: '1',
      type: 'user',
      timestamp: '2026-02-10T14:32:10Z',
      content: 'What are the best practices for implementing AI governance in our organization?',
    },
    {
      id: '2',
      type: 'system',
      timestamp: '2026-02-10T14:32:11Z',
      content: 'Executing AI Governance Assistant v2.3...',
    },
    {
      id: '3',
      type: 'intermediate-result',
      timestamp: '2026-02-10T14:32:12Z',
      data: {
        query: 'AI governance best practices',
        results: [
          { title: 'AI Ethics Framework 2025', relevance: 0.94 },
          { title: 'Enterprise AI Guidelines', relevance: 0.89 },
          { title: 'Regulatory Compliance Checklist', relevance: 0.85 },
        ],
      },
      metadata: {
        stepName: 'Knowledge Base Search Results',
        duration: '0.78s',
      },
    },
    {
      id: '4',
      type: 'ai-response',
      timestamp: '2026-02-10T14:32:15Z',
      content: 'Based on the knowledge base and recent regulations, here are the key recommendations for AI governance implementation:\n\n1. Establish clear accountability structures\n2. Implement robust testing and validation processes\n3. Ensure transparency in AI decision-making\n4. Create ongoing monitoring and audit trails\n5. Develop comprehensive documentation practices',
      metadata: {
        model: 'GPT-4o mini',
        tokens: 245,
        cost: 0.0012,
        duration: '2.09s',
      },
    },
    {
      id: '5',
      type: 'execution-trace',
      timestamp: '2026-02-10T14:32:15Z',
      metadata: {
        promptName: 'AI Governance Assistant',
        promptVersion: 'v2.3',
      },
    },
    {
      id: '6',
      type: 'performance-report',
      timestamp: '2026-02-10T14:32:16Z',
      data: {
        metrics: {
          'Total Execution Time': '15.53s',
          'LLM Calls': '3',
          'Total Tokens': '1,247',
          'Estimated Cost': '$0.0062',
          'Cache Hit Rate': '67%',
          'Knowledge Base Queries': '2',
          'Average Latency': '5.18s',
        },
      },
    },
    {
      id: '7',
      type: 'suggestion',
      timestamp: '2026-02-10T14:32:17Z',
      content: 'This prompt could be optimized by caching the knowledge base results. Estimated savings: 40% faster execution, 25% cost reduction.',
      data: {
        action: 'optimize-caching',
        actionLabel: 'Enable Caching',
        estimatedSavings: { time: '6.2s', cost: '$0.0016' },
      },
    },
  ]);

  const handleNodeClick = (node: any) => {
    // Populate the input with a question about the selected node
    const question = `Can you explain what happened in the "${node.name}" step? ${
      node.duration 
        ? `It took ${node.duration}.` 
        : node.startTime && node.endTime 
        ? `It ran from ${node.startTime} to ${node.endTime}.`
        : ''
    }`;
    setChatInput(question);
  };

  const handleMessageAction = (action: string, data: any) => {
    console.log('Action:', action, 'Data:', data);
    // Handle actions like export, compare, optimize, etc.
    switch (action) {
      case 'export':
        alert('Exporting report...');
        break;
      case 'compare':
        alert('Opening comparison view...');
        break;
      case 'optimize-caching':
        alert('Enabling caching optimization...');
        break;
      default:
        console.log('Unknown action:', action);
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    startYRef.current = e.clientY;
    startHeightRef.current = inputHeight;
    e.preventDefault();
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;

      const deltaY = startYRef.current - e.clientY;
      const newHeight = Math.max(100, Math.min(600, startHeightRef.current + deltaY));
      setInputHeight(newHeight);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'ns-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, inputHeight]);

  return (
    <div className="bg-[rgba(255,255,255,0)] content-stretch flex items-start justify-center relative shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] size-full">
      {/* Sidebar Container */}
      <div className="h-full relative rounded-bl-[10px] rounded-tl-[10px] shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] shrink-0 w-[75px]" style={{ backgroundImage: "linear-gradient(90deg, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0.2) 100%), linear-gradient(193.083deg, rgb(28, 47, 78) 27.022%, rgb(18, 66, 126) 38.117%, rgb(13, 48, 91) 98.965%)" }}>
        
        {/* Logo at top */}
        <div className="content-stretch flex flex-col h-[66px] items-start overflow-clip relative shrink-0 w-full">
          <div className="h-[65.984px] relative shrink-0 w-full">
            <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage} />
          </div>
        </div>

        {/* Active Trace button */}
        <div className="bg-[#fccd3d] h-[77px] relative shrink-0 w-full">
          <div className="absolute inset-0 pointer-events-none rounded-[inherit] shadow-[inset_0px_4px_4px_0px_rgba(0,0,0,0.25)]" />
          <div className="absolute content-stretch flex flex-col h-[25px] items-start left-[22px] top-[13px] w-[26px]">
            <div className="h-[25px] overflow-clip relative shrink-0 w-full">
              <div className="absolute contents inset-0">
                <div className="absolute inset-0 mix-blend-multiply">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 26 25">
                    <g style={{ mixBlendMode: "multiply" }}>
                      <path d="M26 0H0V25H26V0Z" fill="white" fillOpacity="0.01" />
                    </g>
                  </svg>
                </div>
                <div className="absolute inset-[6.25%]">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22.75 21.8752">
                    <path d={svgPaths.pd073400} fill="#507274" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
          <div className="absolute content-stretch flex flex-col h-[16px] items-start justify-center left-[14px] top-[48px] w-[47px]">
            <div className="h-[20px] relative shrink-0 w-[47px]">
              <p className="-translate-x-1/2 absolute font-['Inter'] font-bold leading-[20px] left-[23.98px] text-[#507274] text-[13px] text-center top-0">Trace</p>
            </div>
          </div>
        </div>

        {/* Variables button */}
        <button className="h-[67px] relative shrink-0 w-full hover:bg-[#fccd3d] hover:h-[77px] transition-all duration-300 ease-in-out group">
          <div className="absolute inset-0 pointer-events-none rounded-[inherit] shadow-[inset_0px_0px_0px_0px_rgba(0,0,0,0)] group-hover:shadow-[inset_0px_4px_4px_0px_rgba(0,0,0,0.25)] transition-all duration-300 ease-in-out" />
          <div className="absolute h-[47px] left-[7.42px] top-[10px] w-[60px] group-hover:top-[15px] transition-all duration-300 ease-in-out">
            <div className="absolute content-stretch flex flex-col h-[23.453px] items-start left-[11px] top-px w-[37px]">
              <div className="h-[23.453px] overflow-clip relative shrink-0 w-full">
                <div className="absolute contents inset-[0_16.23%_15.63%_16.97%]">
                  <div className="absolute inset-[0_16.23%_15.63%_16.97%]">
                    <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24.7178 19.7878">
                      <path d={svgPaths.p2723500} fill="#4ECFD5" className="transition-all duration-300 ease-in-out group-hover:fill-[#507274]" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute content-stretch flex flex-col h-[16px] items-start justify-center left-0 top-[31px] w-[60px] group-hover:top-[33px] transition-all duration-300 ease-in-out">
              <div className="h-[20px] relative shrink-0 w-[60px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-medium leading-[20px] left-[29.7px] text-[#4ecfd5] text-[13px] text-center top-0 transition-all duration-300 ease-in-out group-hover:text-[#507274] group-hover:font-bold">Variables</p>
              </div>
            </div>
          </div>
        </button>

        {/* Tools button */}
        <button className="h-[67px] relative shrink-0 w-full hover:bg-[#fccd3d] hover:h-[77px] transition-all duration-300 ease-in-out group">
          <div className="absolute inset-0 pointer-events-none rounded-[inherit] shadow-[inset_0px_0px_0px_0px_rgba(0,0,0,0)] group-hover:shadow-[inset_0px_4px_4px_0px_rgba(0,0,0,0.25)] transition-all duration-300 ease-in-out" />
          <div className="absolute h-[47px] left-[7.42px] top-[10px] w-[60px] group-hover:top-[15px] transition-all duration-300 ease-in-out">
            <div className="absolute content-stretch flex flex-col h-[23px] items-start left-[17px] top-px w-[25px]">
              <div className="h-[23px] overflow-clip relative shrink-0 w-full">
                <div className="absolute contents inset-0">
                  <div className="absolute inset-0 mix-blend-multiply">
                    <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 25 23">
                      <g style={{ mixBlendMode: "multiply" }}>
                        <path d="M25 0H0V23H25V0Z" fill="white" fillOpacity="0.01" />
                      </g>
                    </svg>
                  </div>
                  <div className="absolute inset-[6.25%]">
                    <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.8752 20.125">
                      <path d={svgPaths.p2442da00} fill="#4ECFD5" className="transition-all duration-300 ease-in-out group-hover:fill-[#507274]" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute content-stretch flex flex-col h-[16px] items-start justify-center left-0 top-[31px] w-[60px] group-hover:top-[33px] transition-all duration-300 ease-in-out">
              <div className="h-[20px] relative shrink-0 w-[60px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-medium leading-[20px] left-[29.7px] text-[#4ecfd5] text-[13px] text-center top-0 transition-all duration-300 ease-in-out group-hover:text-[#507274] group-hover:font-bold">Tools</p>
              </div>
            </div>
          </div>
        </button>

        {/* Data button */}
        <button className="h-[67px] relative shrink-0 w-full hover:bg-[#fccd3d] hover:h-[77px] transition-all duration-300 ease-in-out group">
          <div className="absolute inset-0 pointer-events-none rounded-[inherit] shadow-[inset_0px_0px_0px_0px_rgba(0,0,0,0)] group-hover:shadow-[inset_0px_4px_4px_0px_rgba(0,0,0,0.25)] transition-all duration-300 ease-in-out" />
          <div className="absolute h-[47px] left-[7.42px] top-[10px] w-[60px] group-hover:top-[15px] transition-all duration-300 ease-in-out">
            <div className="absolute content-stretch flex flex-col h-[27px] items-start left-[15px] top-0 w-[28px]">
              <div className="h-[27px] overflow-clip relative shrink-0 w-full">
                <div className="absolute contents inset-0">
                  <div className="absolute inset-0 mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[0px_0px] mask-size-[28px_27px] mix-blend-multiply" style={{ maskImage: `url('${imgVector}')` }}>
                    <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 28 27">
                      <g style={{ mixBlendMode: "multiply" }}>
                        <path d="M28 0H0V27H28V0Z" fill="white" fillOpacity="0.01" />
                      </g>
                    </svg>
                  </div>
                  <div className="absolute contents inset-[3.13%_3.12%_3.13%_3.13%]">
                    <div className="absolute inset-[34.38%_34.38%_28.13%_34.38%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-9.625px_-9.281px] mask-size-[28px_27px]" style={{ maskImage: `url('${imgVector}')` }}>
                      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.75 10.125">
                        <path d={svgPaths.p37a9d580} fill="#4ECFD5" className="transition-all duration-300 ease-in-out group-hover:fill-[#507274]" />
                      </svg>
                    </div>
                    <div className="absolute inset-[43.75%_61.54%_8.36%_3.13%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-0.875px_-11.813px] mask-size-[28px_27px]" style={{ maskImage: `url('${imgVector}')` }}>
                      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.8939 12.9302">
                        <path d={svgPaths.p28523180} fill="#4ECFD5" className="transition-all duration-300 ease-in-out group-hover:fill-[#507274]" />
                      </svg>
                    </div>
                    <div className="absolute inset-[61.54%_8.36%_3.13%_43.75%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-12.25px_-16.616px] mask-size-[28px_27px]" style={{ maskImage: `url('${imgVector}')` }}>
                      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.409 9.5407">
                        <path d={svgPaths.p38fec300} fill="#4ECFD5" className="transition-all duration-300 ease-in-out group-hover:fill-[#507274]" />
                      </svg>
                    </div>
                    <div className="absolute inset-[8.36%_3.12%_43.75%_61.54%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-17.231px_-2.257px] mask-size-[28px_27px]" style={{ maskImage: `url('${imgVector}')` }}>
                      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.8939 12.9301">
                        <path d={svgPaths.pf757880} fill="#4ECFD5" className="transition-all duration-300 ease-in-out group-hover:fill-[#507274]" />
                      </svg>
                    </div>
                    <div className="absolute inset-[3.13%_43.75%_61.54%_8.36%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-2.341px_-0.844px] mask-size-[28px_27px]" style={{ maskImage: `url('${imgVector}')` }}>
                      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.409 9.54075">
                        <path d={svgPaths.p38511e00} fill="#4ECFD5" className="transition-all duration-300 ease-in-out group-hover:fill-[#507274]" />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute content-stretch flex flex-col h-[16px] items-start justify-center left-0 top-[31px] w-[60px] group-hover:top-[33px] transition-all duration-300 ease-in-out">
              <div className="h-[20px] relative shrink-0 w-[60px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-medium leading-[20px] left-[29.7px] text-[#4ecfd5] text-[13px] text-center top-0 transition-all duration-300 ease-in-out group-hover:text-[#507274] group-hover:font-bold">Data</p>
              </div>
            </div>
          </div>
        </button>

        {/* Gripper icon (placeholder) */}
        <div className="relative shrink-0 w-full">
          <div className="flex flex-row items-center justify-center size-full">
            <div className="content-stretch flex items-center justify-center px-[8px] py-[3px] relative w-full">
              <div className="flex items-center justify-center relative shrink-0">
                <div className="flex-none rotate-180">
                  <div className="h-[54px] relative w-[24px]">
                    <div className="absolute flex items-center justify-center left-px size-[24px] top-[25px]">
                      <div className="-rotate-90 flex-none">
                        <div className="content-stretch flex flex-col items-start relative size-[24px]">
                          <div className="h-[24px] overflow-clip relative shrink-0 w-full">
                            <div className="absolute contents inset-[45.83%_20.83%_45.83%_45.83%]">
                              <div className="absolute inset-[45.83%]">
                                <div className="absolute inset-[-50%]">
                                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 4">
                                    <path d={svgPaths.p32cd9cf0} stroke="white" strokeLinecap="round" strokeWidth="2" />
                                  </svg>
                                </div>
                              </div>
                              <div className="absolute inset-[45.83%_20.83%_45.83%_70.83%]">
                                <div className="absolute inset-[-50%]">
                                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 4">
                                    <path d={svgPaths.p32cd9cf0} stroke="white" strokeLinecap="round" strokeWidth="2" />
                                  </svg>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="absolute flex items-center justify-center left-px size-[24px] top-[13px]">
                      <div className="-rotate-90 flex-none">
                        <div className="content-stretch flex flex-col items-start relative size-[24px]">
                          <div className="h-[24px] overflow-clip relative shrink-0 w-full">
                            <div className="absolute contents inset-[45.83%_20.83%_45.83%_45.83%]">
                              <div className="absolute inset-[45.83%]">
                                <div className="absolute inset-[-50%]">
                                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 4">
                                    <path d={svgPaths.p32cd9cf0} stroke="white" strokeLinecap="round" strokeWidth="2" />
                                  </svg>
                                </div>
                              </div>
                              <div className="absolute inset-[45.83%_20.83%_45.83%_70.83%]">
                                <div className="absolute inset-[-50%]">
                                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4 4">
                                    <path d={svgPaths.p32cd9cf0} stroke="white" strokeLinecap="round" strokeWidth="2" />
                                  </svg>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats section */}
        <div className="absolute bottom-[70px] left-0 right-0 content-stretch flex flex-col gap-[10px] items-center p-[10px] w-full">
          {/* 27 Approve */}
          <button className="content-stretch flex flex-col h-[58.031px] items-start pb-px pr-[0.031px] rounded-[6px] w-[63.031px] hover:bg-white/10 transition-colors cursor-pointer">
            <div className="content-stretch flex flex-col h-[55px] items-start justify-center relative shrink-0 w-full">
              <div className="h-[21px] relative shrink-0 w-[63px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-black leading-[20px] left-[31.81px] text-[#acb9c0] text-[16px] text-center top-0">27</p>
              </div>
              <div className="h-[20px] relative shrink-0 w-[63px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-bold leading-[20px] left-[31.97px] text-[#acb9c0] text-[13px] text-center top-0">Approve</p>
              </div>
            </div>
          </button>

          {/* 1.2k Likes */}
          <button className="content-stretch flex flex-col h-[57.938px] items-start pb-px pr-[0.016px] rounded-[6px] w-[63.016px] hover:bg-white/10 transition-colors cursor-pointer">
            <div className="content-stretch flex flex-col h-[55px] items-start justify-center relative shrink-0 w-full">
              <div className="h-[20px] relative shrink-0 w-[63px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-bold leading-[20px] left-[31.53px] text-[#acb9c0] text-[14px] text-center top-0">1.2k</p>
              </div>
              <div className="h-[20px] relative shrink-0 w-[63px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-bold leading-[20px] left-[31.58px] text-[#acb9c0] text-[14px] text-center top-0">Likes</p>
              </div>
            </div>
          </button>

          {/* 20 Mixes */}
          <button className="h-[58.031px] rounded-[6px] w-[63.016px] hover:bg-white/10 transition-colors cursor-pointer">
            <div className="content-stretch flex flex-col h-[55px] items-start justify-center w-[63px]">
              <div className="h-[20px] relative shrink-0 w-[63px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-bold leading-[20px] left-[32.14px] text-[#acb9c0] text-[14px] text-center top-0">20</p>
              </div>
              <div className="h-[20px] relative shrink-0 w-[63px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-bold leading-[20px] left-[31.69px] text-[#acb9c0] text-[14px] text-center top-0">Mixes</p>
              </div>
            </div>
          </button>

          {/* 232 Follows */}
          <button className="content-stretch flex flex-col h-[58.016px] items-start pb-px pr-[0.016px] rounded-[6px] w-[63.016px] hover:bg-white/10 transition-colors cursor-pointer">
            <div className="content-stretch flex flex-col h-[55px] items-start justify-center relative shrink-0 w-full">
              <div className="h-[20px] relative shrink-0 w-[63px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-bold leading-[20px] left-[31.94px] text-[#acb9c0] text-[14px] text-center top-0">232</p>
              </div>
              <div className="h-[20px] relative shrink-0 w-[63px]">
                <p className="-translate-x-1/2 absolute font-['Inter'] font-bold leading-[20px] left-[31.98px] text-[#acb9c0] text-[14px] text-center top-0">Follows</p>
              </div>
            </div>
          </button>
        </div>

        {/* Settings button at bottom */}
        <button className="absolute content-stretch flex flex-col h-[29.547px] items-start left-[23px] bottom-[20px] w-[28.016px] hover:bg-white/5 rounded transition-colors">
          <div className="h-[29.547px] overflow-clip relative shrink-0 w-full">
            <div className="absolute contents inset-0">
              <div className="absolute inset-0 mix-blend-multiply">
                <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 28.0156 29.5469">
                  <g style={{ mixBlendMode: "multiply" }}>
                    <path d={svgPaths.p13379f2} fill="white" fillOpacity="0.01" />
                  </g>
                </svg>
              </div>
              <div className="absolute contents inset-[6.25%_0_6.25%_7.59%]">
                <div className="absolute bottom-[6.25%] left-[56.25%] right-0 top-1/2">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12.2569 12.9268">
                    <path d={svgPaths.p2746f500} fill="#B5CCCE" />
                  </svg>
                </div>
                <div className="absolute inset-[31.25%]">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 10.5059 11.0801">
                    <path d={svgPaths.pb931d00} fill="#B5CCCE" />
                  </svg>
                </div>
                <div className="absolute inset-[6.25%_8.5%_6.25%_7.59%]">
                  <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 23.5089 25.8534">
                    <path d={svgPaths.pa59fe40} fill="#B5CCCE" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </button>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col h-full">
        {/* Chat messages area */}
        <div className="flex-1 bg-white rounded-tr-[10px] shadow-[inset_5px_5px_10px_0px_rgba(0,0,0,0.25)] border border-[#8e98a8] overflow-auto p-6">
          <div className="space-y-6">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onNodeClick={handleNodeClick}
                onAction={handleMessageAction}
              />
            ))}
          </div>
        </div>

        {/* Action bar - entire bar is draggable gripper */}
        <div 
          onMouseDown={handleMouseDown}
          className={`bg-[#e5e1dd] h-[58px] shrink-0 flex items-center px-2 gap-[15px] cursor-ns-resize hover:bg-[#d5d1cd] transition-all ${
            isDragging ? 'bg-[#c5c1bd]' : ''
          }`}
          title="Drag to resize input area"
        >
          {/* Gripper handle icon - visual indicator */}
          <div
            className={`h-[40px] w-[25px] rounded transition-all flex items-center justify-center pointer-events-none ${
              isDragging ? 'bg-black/10' : ''
            }`}
            aria-label="Resize input area"
          >
            <img src={gripperImage} alt="" className="w-full h-auto object-contain" />
          </div>

          {/* Send button */}
          <button 
            onMouseDown={(e) => e.stopPropagation()}
            className="bg-[#507274] flex items-center justify-center px-[5px] py-[7px] rounded-[6px] h-[40px] w-[44px] border border-[#758e87] hover:bg-[#5e8486] transition-colors"
          >
            <div className="rotate-[-88.53deg] skew-x-[0.82deg]">
              <svg className="w-[23px] h-[29px]" fill="none" viewBox="0 0 17.494 21.5167">
                <path d="M0 0L17.494 10.758L0 21.517L0 13.514L12.495 10.758L0 8.003L0 0Z" fill="#FFDE30" />
              </svg>
            </div>
          </button>

          {/* (10) Approve button */}
          <button 
            onMouseDown={(e) => e.stopPropagation()}
            className="bg-[#1c2f4e] flex items-center justify-center px-[10px] py-[7px] rounded-[6px] h-[40px] border border-[#758e87] hover:bg-[#243a5d] transition-colors"
          >
            <p className="font-['Inter'] font-bold text-[16px] text-white leading-[20px]">
              <span className="font-medium">(10) </span>
              <span>Approve</span>
            </p>
          </button>

          {/* + button */}
          <button 
            onMouseDown={(e) => e.stopPropagation()}
            className="bg-[#507274] flex items-center justify-center px-[5px] py-[7px] rounded-[6px] h-[40px] w-[44px] border border-[#758e87] hover:bg-[#5e8486] transition-colors"
          >
            <p className="font-['Inter'] font-medium text-[36px] text-white leading-[20px]">+</p>
          </button>

          {/* Console button */}
          <button 
            onMouseDown={(e) => e.stopPropagation()}
            className="bg-[#1c2f4e] flex items-center justify-center px-[10px] py-[7px] rounded-[6px] h-[40px] border border-[#758e87] hover:bg-[#243a5d] transition-colors"
          >
            <p className="font-['Inter'] font-bold text-[16px] text-white leading-[20px]">Console</p>
          </button>
        </div>

        {/* Resizable input area */}
        <div 
          className="bg-[#b5ccce] shadow-[inset_5px_5px_10px_0px_rgba(0,0,0,0.25)] transition-all"
          style={{ height: `${inputHeight}px`, transitionDuration: isDragging ? '0ms' : '100ms' }}
        >
          <div className="p-4 h-full flex flex-col gap-2">
            <textarea
              className="w-full flex-1 bg-white border border-[#8e98a8] rounded-md p-3 resize-none focus:outline-none focus:ring-2 focus:ring-[#507274] font-['Inter'] text-[14px]"
              placeholder="Type your message here..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
            />
          </div>
        </div>

        {/* Bottom bar with GPT-4.1 selector */}
        <div className="bg-[#b5ccce] h-[52px] rounded-br-[10px] shrink-0 flex items-center justify-between px-5">
          <button className="bg-[#e5f1ec] border border-[#bcbcbc] h-[34px] px-5 rounded-[4px] shadow-[2px_3px_10px_0px_rgba(0,0,0,0.15)] font-['Inter'] font-bold text-[18px] text-[#10455f] hover:bg-[#d5e1dc] transition-colors">
            GPT-4.1
          </button>
          <div className="text-[#10455f] text-sm opacity-60">
            {isDragging ? `${inputHeight}px` : ''}
          </div>
        </div>
      </div>
    </div>
  );
}