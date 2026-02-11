import { useState } from 'react';
import svgPaths from '../../imports/svg-5zxoz9hv2f';
import imgImage390 from 'figma:asset/a0c698671eb795bc84024e87ad7c0b231c53115c.png';

interface TraceNode {
  id: string;
  name: string;
  type: 'function' | 'task' | 'model' | 'analysis';
  startTime?: string;
  endTime?: string;
  duration?: string;
  children?: TraceNode[];
}

interface PromptTrace {
  promptName: string;
  promptVersion?: string;
  executionTime: string;
  totalDuration: string;
  status: 'success' | 'error' | 'pending';
  rootNode: TraceNode;
}

const traceData: PromptTrace = {
  promptName: 'AI Governance Assistant',
  promptVersion: 'v2.3',
  executionTime: '2026-02-10 14:32:15',
  totalDuration: '15.53s',
  status: 'success',
  rootNode: {
    id: 'root',
    name: 'Task',
    type: 'task',
    startTime: '9.13s',
    endTime: '15.53s',
    children: [
      {
        id: 'process-user',
        name: 'ProcessUser Message',
        type: 'task',
        startTime: '9.49s',
        endTime: '15.53s',
        children: [
          {
            id: 'search-kb',
            name: 'search_knowledge_base',
            type: 'function',
            startTime: '0.78s',
            endTime: '0.09s',
          },
          {
            id: 'calculate',
            name: 'Calculate',
            type: 'function',
            startTime: '0.53s',
            endTime: '1.37s',
          },
          {
            id: 'llm-followup',
            name: 'LLMFollowup',
            type: 'task',
            startTime: '9.48s',
            endTime: '15.53s',
            children: [
              {
                id: 'copilot',
                name: 'Copilot (GPT-4o mini)',
                type: 'model',
                startTime: '2.02s',
                endTime: '2.09s',
              },
            ],
          },
        ],
      },
      {
        id: 'intent-1',
        name: 'Intent Classification',
        type: 'analysis',
        duration: '0.08s',
      },
      {
        id: 'closed-qa-1',
        name: 'Closed QA',
        type: 'analysis',
        duration: '0.27s',
      },
      {
        id: 'intent-2',
        name: 'Intent Classification',
        type: 'analysis',
        duration: '0.08s',
      },
      {
        id: 'closed-qa-2',
        name: 'Closed QA',
        type: 'analysis',
        duration: '0.27s',
      },
      {
        id: 'intent-3',
        name: 'Intent Classification',
        type: 'analysis',
        duration: '0.08s',
      },
    ],
  },
};

function NodeIcon({ type }: { type: TraceNode['type'] }) {
  const colors = {
    function: '#d29207',
    task: '#8ec1b3',
    model: '#d7c0e1',
    analysis: '#7aad63',
  };

  const borders = {
    function: 'none',
    task: '#8ec1b3',
    model: '#53176c',
    analysis: 'none',
  };

  if (type === 'function') {
    return (
      <div className="relative size-[28px] shrink-0">
        <div
          className="absolute left-0 rounded-[6px] shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] size-[28px] top-0"
          style={{ backgroundColor: colors.function }}
        />
        <div className="absolute left-[4px] size-[21px] top-[3px]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21 21">
            <g clipPath="url(#clip0_5_116)">
              <g>
                <path d={svgPaths.pb4edfd8} fill="white" />
                <path d={svgPaths.p1795b490} fill="white" />
                <path d={svgPaths.pffa00} fill="white" />
                <path d={svgPaths.p2410d380} fill="white" />
                <path d={svgPaths.p2f1db400} fill="white" />
              </g>
            </g>
            <defs>
              <clipPath id="clip0_5_116">
                <rect fill="white" height="21" width="21" />
              </clipPath>
            </defs>
          </svg>
        </div>
      </div>
    );
  }

  if (type === 'task') {
    return (
      <div className="relative size-[28px] shrink-0">
        <div
          className="absolute border border-solid left-0 rounded-[6px] shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] size-[28px] top-0"
          style={{ backgroundColor: colors.task, borderColor: borders.task }}
        />
        <div className="absolute flex flex-col font-['Inter:Bold',sans-serif] font-bold justify-center leading-[0] left-[4px] not-italic text-[20px] text-white top-[6px] whitespace-nowrap">
          <p className="leading-[16px]">( )</p>
        </div>
      </div>
    );
  }

  if (type === 'model') {
    return (
      <div className="relative size-[28px] shrink-0">
        <div
          className="absolute border border-solid left-0 rounded-[6px] shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] size-[28px] top-0"
          style={{ backgroundColor: colors.model, borderColor: borders.model }}
        />
        <div className="absolute h-[31px] left-[-3px] top-[-3px] w-[33px]">
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <img alt="" className="absolute h-[106.45%] left-0 max-w-none top-0 w-full" src={imgImage390} />
          </div>
        </div>
      </div>
    );
  }

  // analysis
  return (
    <div className="relative size-[28px] shrink-0">
      <div
        className="absolute left-0 rounded-[6px] shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] size-[28px] top-0"
        style={{ backgroundColor: colors.analysis }}
      />
      <div className="absolute left-[5px] size-[21px] top-[4px]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21 21">
          <g>
            <rect fill="white" fillOpacity="0.01" height="21" width="21" />
            <g>
              <path d={svgPaths.p35165c00} fill="white" />
              <path d={svgPaths.p1f5a0e70} fill="white" />
              <path d={svgPaths.p2094b372} fill="white" />
              <path d={svgPaths.p324e96f0} fill="white" />
            </g>
          </g>
        </svg>
      </div>
    </div>
  );
}

interface TreeNodeProps {
  node: TraceNode;
  level: number;
  onNodeClick: (node: TraceNode) => void;
  forceExpanded?: boolean;
}

function TreeNode({ node, level, onNodeClick, forceExpanded }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;

  const handleNodeClick = () => {
    onNodeClick(node);
  };

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hasChildren) {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div className="select-none">
      <div
        className="flex items-center gap-2 py-1 hover:bg-gray-100 rounded cursor-pointer group transition-colors"
        style={{ paddingLeft: `${level * 20 + 4}px` }}
      >
        {/* Expand/Collapse chevron */}
        <button
          onClick={handleToggle}
          className={`flex items-center justify-center w-4 h-4 shrink-0 transition-transform ${
            hasChildren ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
        >
          <svg
            className={`w-3 h-3 text-gray-500 transition-transform ${
              isExpanded ? 'rotate-90' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        {/* Node icon - clickable */}
        <button
          onClick={handleNodeClick}
          className="hover:scale-110 transition-transform focus:outline-none focus:ring-2 focus:ring-[#4066e3] rounded"
          title={`Click to ask about ${node.name}`}
        >
          <NodeIcon type={node.type} />
        </button>

        {/* Node content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <p className="font-['Inter:Semi_Bold',sans-serif] font-semibold text-[14px] text-[#171717] truncate">
              {node.name}
            </p>
            {node.duration && (
              <p className="font-['Inter',sans-serif] text-[13px] text-gray-600 whitespace-nowrap">
                {node.duration}
              </p>
            )}
            {node.startTime && node.endTime && (
              <p className="font-['Inter',sans-serif] text-[13px] whitespace-nowrap">
                <span className="font-bold text-[#4066e3]">{node.startTime}</span>
                <span className="text-gray-600"> → {node.endTime}</span>
              </p>
            )}
          </div>
        </div>

        {/* Ask question icon - appears on hover */}
        <button
          onClick={handleNodeClick}
          className="opacity-0 group-hover:opacity-100 transition-opacity mr-2 p-1 hover:bg-[#4066e3] hover:text-white rounded"
          title="Ask about this node"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </button>
      </div>

      {/* Children */}
      {hasChildren && (isExpanded || forceExpanded) && (
        <div className="relative">
          {/* Vertical line connector */}
          <div
            className="absolute top-0 bottom-0 w-px bg-gray-300"
            style={{ left: `${level * 20 + 20}px` }}
          />
          {node.children!.map((child) => (
            <TreeNode key={child.id} node={child} level={level + 1} onNodeClick={onNodeClick} />
          ))}
        </div>
      )}
    </div>
  );
}

interface TraceTreeInteractiveProps {
  onNodeClick?: (node: TraceNode) => void;
}

export default function TraceTreeInteractive({ onNodeClick }: TraceTreeInteractiveProps) {
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [expandAll, setExpandAll] = useState(false);

  const handleNodeClick = (node: TraceNode) => {
    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  const toggleExpandAll = () => {
    setExpandAll(!expandAll);
  };

  const statusColors = {
    success: '#7aad63',
    error: '#e74c3c',
    pending: '#f39c12',
  };

  return (
    <div className="w-full h-full flex flex-col bg-white rounded-lg overflow-hidden">
      {/* Collapsible Header */}
      <div className="border-b border-gray-200">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors duration-200"
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {/* Collapse/Expand Icon */}
            <svg
              className={`w-4 h-4 text-gray-500 transition-transform duration-500 ease-out shrink-0 ${
                isCollapsed ? '' : 'rotate-90'
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>

            {/* Prompt Info */}
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <h3 className="font-['Inter:Semi_Bold',sans-serif] font-semibold text-[14px] text-[#171717] truncate">
                  {traceData.promptName}
                </h3>
                {traceData.promptVersion && (
                  <span className="px-2 py-0.5 bg-[#4066e3] text-white text-[11px] font-['Inter:Medium',sans-serif] rounded-full shrink-0">
                    {traceData.promptVersion}
                  </span>
                )}
              </div>
            </div>

            {/* Status Indicator */}
            <div className="flex items-center gap-2 shrink-0">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: statusColors[traceData.status] }}
                title={traceData.status}
              />
              <span className="font-['Inter:Medium',sans-serif] text-[12px] text-gray-600">
                {traceData.totalDuration}
              </span>
            </div>
          </div>
        </button>

        {/* Metadata Row - Only show when expanded with smooth animation */}
        <div
          className={`overflow-hidden transition-all duration-500 ease-out ${
            isCollapsed ? 'max-h-0 opacity-0' : 'max-h-20 opacity-100'
          }`}
        >
          <div className="px-4 pb-3 flex items-center justify-between">
            <div className="flex items-center gap-4 text-[12px] text-gray-600 font-['Inter',sans-serif]">
              <span>Executed: {traceData.executionTime}</span>
            </div>

            {/* Expand/Collapse All Button */}
            <button
              onClick={toggleExpandAll}
              className="flex items-center gap-1 px-2 py-1 text-[12px] font-['Inter:Medium',sans-serif] text-[#4066e3] hover:bg-blue-50 rounded transition-colors"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {expandAll ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                )}
              </svg>
              {expandAll ? 'Collapse All' : 'Expand All'}
            </button>
          </div>
        </div>
      </div>

      {/* Tree Content with smooth animation */}
      <div
        className={`overflow-hidden transition-all duration-500 ease-out ${
          isCollapsed ? 'max-h-0 opacity-0' : 'max-h-[2000px] opacity-100'
        }`}
      >
        <div className="overflow-auto">
          <div className="p-2">
            <TreeNode
              node={traceData.rootNode}
              level={0}
              onNodeClick={handleNodeClick}
              forceExpanded={expandAll}
            />
          </div>
        </div>
      </div>

      {/* Collapsed Summary with smooth animation */}
      <div
        className={`overflow-hidden transition-all duration-500 ease-out ${
          isCollapsed ? 'max-h-20 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-4 py-2 text-[12px] text-gray-500 font-['Inter',sans-serif]">
          Click to expand trace details
        </div>
      </div>
    </div>
  );
}