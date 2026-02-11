import { useState, useEffect } from 'react';
import svgPaths from '../imports/svg-pbf59edrh7';
import imgScoreCard from "figma:asset/79f4f285779fa42640cd978e390d19834e64f5f9.png";
import imgLightbulbs from "figma:asset/150aaf9d5ccdf1b1973eebaa4f307057de9695dd.png";
import imgUserAvatar from "figma:asset/1d1c6e47491f6726f6303aa8c515da81db485c50.png";
import imgChatPlaceholder from "figma:asset/db72500973528d37a484b75ad3d64518f59541e7.png";
import Header from './components/Header';
import VerticalSidebar from './components/VerticalSidebar';

interface NavTabProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}

function NavTab({ icon, label, active, onClick }: NavTabProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 px-4 py-5 font-semibold text-base transition-colors ${
        active ? 'text-[#4066e3]' : 'text-[#155258] hover:text-[#4066e3]'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function ConsoleIcon({ active }: { active?: boolean }) {
  const strokeColor = active ? '#4066E3' : '#155258';
  return (
    <svg className="w-[21px] h-[22px]" fill="none" viewBox="0 0 21.3124 21.7778">
      <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.77603" stroke={strokeColor} strokeWidth="1.2" transform="rotate(90 15.9843 8.16667)" width="3.62963" x="15.9843" y="8.16667" />
      <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.77603" stroke={strokeColor} strokeWidth="1.2" transform="rotate(90 15.9843 15.4259)" width="3.62963" x="15.9843" y="15.4259" />
      <rect fill="#7E869E" fillOpacity="0.25" height="3.55207" rx="1.77603" stroke={strokeColor} strokeWidth="1.2" transform="rotate(-90 2.66405 6.35185)" width="3.62963" x="2.66405" y="6.35185" />
      <path d={svgPaths.pa05f480} stroke={strokeColor} strokeWidth="1.2" />
      <path d={svgPaths.p12182880} stroke={strokeColor} strokeWidth="1.2" />
    </svg>
  );
}

function VariablesIcon() {
  return (
    <svg className="w-[19px] h-[19px]" fill="none" viewBox="0 0 19 19">
      <path d={svgPaths.p1fe03340} stroke="#155258" />
      <path d={svgPaths.p137b6870} stroke="#155258" />
      <path d={svgPaths.p1e42fb00} stroke="#155258" />
    </svg>
  );
}

function MetadataIcon() {
  return (
    <svg className="w-[22px] h-[22px]" fill="none" viewBox="0 0 22 22">
      <path d={svgPaths.p68ff600} fill="#7E869E" fillOpacity="0.25" stroke="#155258" />
      <ellipse cx="11" cy="6.41667" rx="6.41667" ry="2.75" stroke="#155258" strokeWidth="1.2" />
      <path d={svgPaths.p2ddb2d00} stroke="#155258" strokeLinecap="square" strokeWidth="1.2" />
      <path d={svgPaths.p1e08bb80} stroke="#155258" strokeWidth="1.2" />
    </svg>
  );
}

function MeatballsMenu({ opacity = 1 }: { opacity?: number }) {
  return (
    <svg className="w-6 h-6 -rotate-90" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="1" stroke="#767676" strokeLinecap="round" strokeOpacity={opacity} strokeWidth="2" />
      <circle cx="6" cy="12" r="1" stroke="#767676" strokeLinecap="round" strokeOpacity={opacity} strokeWidth="2" />
      <circle cx="18" cy="12" r="1" stroke="#767676" strokeLinecap="round" strokeOpacity={opacity} strokeWidth="2" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg className="w-[27px] h-[28px]" fill="none" viewBox="0 0 21.934 18.455">
      <path d={svgPaths.p2a20100} fill="#E4D48E" stroke="#D29207" />
    </svg>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('composer');
  const [systemRole, setSystemRole] = useState(
    "EXAMPLE of System Role Instructions\nYou are a helpful and informative AI assistant that specializes (enter subject). You can use tool_choice: get_weather(city), calculate_tax(amount).\n\nProvide concise, polite responses."
  );
  const [userRole, setUserRole] = useState("Start customizing your prompt text here or ask Copilot for assistance.");
  const [selectedRole, setSelectedRole] = useState("Select Role");
  const [promptTitle] = useState("prompt_title: Solar energy system designer with expertise in off-grid installations for");
  const [leftColumnWidth, setLeftColumnWidth] = useState(646);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    e.preventDefault();
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;
    
    // Calculate new width based on mouse position relative to sidebar (84px offset)
    const newWidth = e.clientX - 84;
    
    // Set min and max widths for usability
    if (newWidth >= 400 && newWidth <= 1200) {
      setLeftColumnWidth(newWidth);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Add and remove mouse event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div className="relative w-full h-screen bg-[#e5e1dd] overflow-hidden">
      {/* Sidebar */}
      <VerticalSidebar />

      {/* Header - Using imported Component23 */}
      <div className="absolute left-20 top-0 right-0 h-[73px]">
        <Header />
      </div>

      {/* Prompt Title Bar */}
      <div className="absolute left-20 top-[74px] right-0 h-[90px] bg-white flex items-center px-8 gap-10">
        <p className="text-[22px] font-semibold text-black max-w-[874px] truncate">
          {promptTitle}
        </p>
        <div className="flex items-center justify-center h-[31px] px-4 bg-[#d1def7] border border-[#4066e3] rounded-full">
          <span className="text-[16px] font-bold text-[#4e68d2]">Editing Version 8</span>
        </div>
        <div className="flex items-center gap-2">
          <WarningIcon />
          <span className="text-[14px] font-bold text-[#4066e3]">No tags +</span>
        </div>
        <span className="text-[16px] font-medium text-black">ID: PR-1956</span>
        <span className="text-[16px] font-medium text-black">Author: John Holt</span>
        <div className="w-[114px] h-[33px] rounded-md border border-[#4066e3] overflow-hidden">
          <img src={imgScoreCard} alt="Score" className="w-full h-full object-cover" />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="absolute left-[84px] top-[161px] right-4 bottom-20 flex gap-0">
        {/* Left Panel - System Role, User Role, Select Role */}
        <div className="bg-white rounded-tl-[10px] border border-[#c0bdcf] p-6 overflow-y-auto" style={{ width: leftColumnWidth, flexShrink: 0 }}>
          {/* System Role Section */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <MeatballsMenu opacity={0.5} />
              <div className="flex-1 bg-white border border-[#8e98a8] rounded-md shadow-md h-[43px] flex items-center px-4">
                <span className="text-[18px] font-bold text-[#171717]">System Role</span>
              </div>
              <div className="bg-white border border-[#8e98a8] rounded-md shadow-md h-[43px] px-6 flex items-center">
                <span className="text-[16px] font-bold text-[#5a5a5a]">Functions / Tools</span>
              </div>
            </div>
            
            <div className="relative">
              <div className="absolute -left-10 top-0 w-[37px] h-[37px]">
                <svg className="w-full h-full" fill="none" viewBox="0 0 37 37">
                  <path d={svgPaths.p32331f80} fill="#33363F" />
                </svg>
              </div>
              <textarea
                value={systemRole}
                onChange={(e) => setSystemRole(e.target.value)}
                className="w-full h-[189px] p-4 bg-white rounded-md shadow-md text-[16px] font-semibold text-black leading-[25px] resize-none border border-gray-200 focus:outline-none focus:border-[#4066e3]"
              />
            </div>
          </div>

          {/* User Role Section */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <MeatballsMenu />
              <div className="flex-1 bg-white border border-[#8e98a8] rounded-md shadow-md h-[43px] flex items-center px-4">
                <span className="text-[18px] font-bold text-[#171717]">User Role</span>
                <WarningIcon />
                <div className="ml-auto flex gap-4 text-[14px] font-bold">
                  <span className="text-[#4066e3]">{'{{variables}}'}</span>
                  <span className="text-[#767676]">{'{{multimedia}}'}</span>
                  <span className="text-[#767676]">{'{{url}}'}</span>
                </div>
              </div>
            </div>
            
            <textarea
              value={userRole}
              onChange={(e) => setUserRole(e.target.value)}
              className="w-full h-[199px] p-4 bg-white rounded-md text-[16px] font-semibold text-black leading-[25px] resize-none border border-gray-200 focus:outline-none focus:border-[#4066e3]"
              placeholder="Start customizing your prompt text here or ask Copilot for assistance."
            />
            
            {/* Attachment icon */}
            <div className="mt-4">
              <svg className="w-[44px] h-[41px]" fill="none" viewBox="0 0 44 41">
                <path d={svgPaths.pf979900} stroke="url(#paint0_linear)" strokeLinecap="round" strokeWidth="2" />
                <defs>
                  <linearGradient id="paint0_linear" x1="27" x2="27" y1="6" y2="33" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#7E72E3" />
                    <stop offset="1" stopColor="#4234B8" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
          </div>

          {/* Select Role Section */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <MeatballsMenu />
              <div className="flex-1 bg-white border-[0.5px] border-[#8e98a8] rounded-md shadow-md h-[43px] flex items-center px-4">
                <span className="text-[18px] font-bold text-[#767676]">Select Role</span>
                <div className="ml-auto flex gap-4 text-[14px] font-semibold">
                  <span className="text-[#4066e3]">{'{{variables}}'}</span>
                  <span className="text-[#767676]">{'{{multimedia}}'}</span>
                  <span className="text-[#767676]">{'{{url}}'}</span>
                </div>
              </div>
            </div>
            
            <div className="bg-white/50 rounded-md shadow-md p-5">
              <p className="text-[16px] font-semibold text-black leading-[25px]">
                Select a role and enter your prompt.
              </p>
            </div>
          </div>
        </div>

        {/* Resizable Gripper/Divider */}
        <div 
          className={`relative w-1 bg-[#c0bdcf] cursor-col-resize hover:bg-[#4066e3] transition-colors flex items-center justify-center group ${isDragging ? 'bg-[#4066e3]' : ''}`}
          onMouseDown={handleMouseDown}
        >
          {/* Gripper dots */}
          <div className="absolute flex flex-col gap-1 opacity-60 group-hover:opacity-100 transition-opacity">
            <div className="w-1 h-1 rounded-full bg-[#767676]" />
            <div className="w-1 h-1 rounded-full bg-[#767676]" />
            <div className="w-1 h-1 rounded-full bg-[#767676]" />
            <div className="w-1 h-1 rounded-full bg-[#767676]" />
            <div className="w-1 h-1 rounded-full bg-[#767676]" />
          </div>
        </div>

        {/* Middle Panel - Response Format */}
        <div className="flex-1 bg-white shadow-inner overflow-hidden">
          <div className="relative h-full flex flex-col">
            {/* Response Format Header */}
            <div className="bg-white p-3 border-b">
              <div className="flex items-center justify-between">
                <div className="bg-white border border-[#8e98a8] rounded-md shadow-md px-4 py-2">
                  <span className="text-[18px] font-bold text-[#171717]">Response Format</span>
                </div>
                <div className="bg-white border border-[#bcbcbc] rounded px-4 py-2">
                  <span className="text-[18px] font-bold text-[#838190]">GPT-4.1</span>
                </div>
                <MeatballsMenu />
              </div>
            </div>

            {/* Center content */}
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="mb-6">
                  <img src={imgLightbulbs} alt="Lightbulbs" className="w-[472px] h-auto mx-auto" />
                </div>
                <p className="text-[24px] font-semibold text-black max-w-[208px] mx-auto">
                  Select RUN to test prompt output.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Chat Placeholder */}
        <div className="w-[700px] bg-white rounded-br-[10px] overflow-hidden shadow-lg">
          <img 
            src={imgChatPlaceholder} 
            alt="AI Governance Assistant Chat" 
            className="w-full h-full object-cover"
          />
        </div>
      </div>

      {/* Bottom Action Bar */}
      <div className="absolute left-[84px] right-4 bottom-0 h-[70px] bg-[#b5ccce] rounded-br-[10px] rounded-tr-[10px] shadow-inner flex items-center justify-between px-6">
        <div className="flex items-center gap-6">
          <div className="bg-white rounded-md shadow-md px-8 py-2 flex items-center gap-2">
            <div className="w-9 h-9 bg-gray-200 rounded-full flex items-center justify-center">
              <span className="text-xl">↩️</span>
            </div>
            <span className="text-[16px] font-bold text-[#5a5a5a]">
              Save Template <span className="text-[#8b8b8b]">⌘ S</span>
            </span>
          </div>
          
          <button className="bg-gradient-to-r from-[#f0b424] to-[#fed141] rounded-md shadow-md px-8 py-3">
            <span className="text-[18px] font-extrabold text-black">
              RUN <span className="font-medium text-[#507274]">⌘ ⏎</span>
            </span>
          </button>
          
          <button className="bg-white rounded-md shadow-md px-8 py-2">
            <span className="text-[16px] font-bold text-[#5a5a5a]">A/B Test</span>
          </button>
        </div>

        <div className="flex items-center gap-4">
          <span className="text-[18px] font-bold text-[#171717]">Export</span>
          <span className="text-[18px] font-bold text-[#171717]">Share</span>
          <span className="text-[18px] font-bold text-[#171717]">Publish</span>
          <MeatballsMenu />
        </div>
      </div>

      {/* User Avatar (bottom left) */}
      <div className="absolute left-[18px] top-[268px]">
        <img src={imgUserAvatar} alt="User" className="w-[47px] h-[44px] rounded-full border border-[#6a9c9e]" />
      </div>
    </div>
  );
}