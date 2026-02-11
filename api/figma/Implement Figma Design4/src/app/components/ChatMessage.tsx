import { useState } from 'react';
import TraceTreeInteractive from './TraceTreeInteractive';

export type MessageType = 
  | 'user' 
  | 'ai-response' 
  | 'execution-trace'
  | 'intermediate-result'
  | 'error'
  | 'warning'
  | 'comparison'
  | 'performance-report'
  | 'suggestion'
  | 'system';

export interface ChatMessageData {
  id: string;
  type: MessageType;
  timestamp: string;
  content?: string;
  data?: any;
  metadata?: {
    promptName?: string;
    promptVersion?: string;
    model?: string;
    tokens?: number;
    cost?: number;
    duration?: string;
  };
}

interface ChatMessageProps {
  message: ChatMessageData;
  onNodeClick?: (node: any) => void;
  onAction?: (action: string, data: any) => void;
}

function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="bg-[#4066e3] text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-semibold shrink-0">
        U
      </div>
      <div className="flex-1">
        <p className="text-gray-800 text-[14px] font-['Inter']">{content}</p>
      </div>
    </div>
  );
}

function AIResponse({ content, metadata }: { content?: string; metadata?: any }) {
  return (
    <div className="flex items-start gap-3">
      <div className="bg-gradient-to-br from-[#1c2f4e] to-[#124276] text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-semibold shrink-0">
        AI
      </div>
      <div className="flex-1">
        <p className="text-gray-800 text-[14px] font-['Inter'] whitespace-pre-wrap">{content}</p>
        {metadata && (
          <div className="mt-2 flex items-center gap-3 text-[11px] text-gray-500 font-['Inter']">
            {metadata.model && <span>Model: {metadata.model}</span>}
            {metadata.tokens && <span>•</span>}
            {metadata.tokens && <span>{metadata.tokens} tokens</span>}
            {metadata.cost && <span>•</span>}
            {metadata.cost && <span>${metadata.cost.toFixed(4)}</span>}
            {metadata.duration && <span>•</span>}
            {metadata.duration && <span>{metadata.duration}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

function ExecutionTrace({ data, onNodeClick }: { data?: any; onNodeClick?: (node: any) => void }) {
  return (
    <div className="flex items-start gap-3">
      <div className="bg-gradient-to-br from-[#1c2f4e] to-[#124276] text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-semibold shrink-0">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      </div>
      <div className="flex-1">
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <TraceTreeInteractive onNodeClick={onNodeClick} />
        </div>
      </div>
    </div>
  );
}

function IntermediateResult({ data, metadata }: { data: any; metadata?: any }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="flex items-start gap-3">
      <div className="bg-[#7aad63] text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-semibold shrink-0">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <div className="flex-1">
        <div className="bg-green-50 border border-green-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-green-100 transition-colors duration-200"
          >
            <div className="flex items-center gap-2">
              <svg
                className={`w-4 h-4 text-green-700 transition-transform duration-500 ease-out ${
                  isExpanded ? 'rotate-90' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <h3 className="text-[13px] font-semibold text-green-800 font-['Inter']">
                {metadata?.stepName || 'Intermediate Result'}
              </h3>
            </div>
            {metadata?.duration && (
              <span className="text-[11px] text-green-600 font-['Inter']">{metadata.duration}</span>
            )}
          </button>
          
          <div 
            className={`overflow-hidden transition-all duration-500 ease-out ${
              isExpanded ? 'max-h-[400px] opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            <div className="px-4 pb-4">
              <pre className="bg-white p-3 rounded border border-green-200 text-[12px] font-mono overflow-x-auto max-h-[300px] overflow-y-auto">
                {JSON.stringify(data, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ErrorMessage({ content, data }: { content?: string; data?: any }) {
  const [isExpanded, setIsExpanded] = useState(true);
  
  return (
    <div className="flex items-start gap-3">
      <div className="bg-red-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-semibold shrink-0">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <div className="flex-1">
        <div className="bg-red-50 border border-red-300 rounded-lg overflow-hidden">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-red-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg
                className={`w-4 h-4 text-red-700 transition-transform ${
                  isExpanded ? 'rotate-90' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <h3 className="text-[13px] font-semibold text-red-800 font-['Inter']">
                Execution Error
              </h3>
            </div>
          </button>
          
          {isExpanded && (
            <div className="px-4 pb-4">
              <p className="text-[13px] text-red-800 font-['Inter'] mb-2">{content}</p>
              {data?.stack && (
                <pre className="bg-white p-3 rounded border border-red-200 text-[11px] font-mono overflow-x-auto max-h-[200px] overflow-y-auto text-red-700">
                  {data.stack}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WarningMessage({ content }: { content?: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="bg-yellow-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-semibold shrink-0">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <div className="flex-1">
        <div className="bg-yellow-50 border border-yellow-300 rounded-lg px-4 py-3">
          <p className="text-[13px] text-yellow-800 font-['Inter']">{content}</p>
        </div>
      </div>
    </div>
  );
}

function PerformanceReport({ data, onAction }: { data: any; onAction?: (action: string, data: any) => void }) {
  const [isExpanded, setIsExpanded] = useState(true);
  
  return (
    <div className="flex items-start gap-3">
      <div className="bg-[#4066e3] text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-semibold shrink-0">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      </div>
      <div className="flex-1">
        <div className="bg-blue-50 border border-blue-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-blue-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg
                className={`w-4 h-4 text-blue-700 transition-transform ${
                  isExpanded ? 'rotate-90' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <h3 className="text-[13px] font-semibold text-blue-800 font-['Inter']">
                Performance Report
              </h3>
            </div>
          </button>
          
          {isExpanded && (
            <div className="px-4 pb-4">
              <div className="bg-white rounded-lg border border-blue-200 overflow-hidden">
                <table className="w-full text-[12px]">
                  <thead className="bg-blue-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold text-blue-900 font-['Inter']">Metric</th>
                      <th className="px-3 py-2 text-right font-semibold text-blue-900 font-['Inter']">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-blue-100">
                    {data?.metrics && Object.entries(data.metrics).map(([key, value]: [string, any]) => (
                      <tr key={key} className="hover:bg-blue-50">
                        <td className="px-3 py-2 text-gray-700 font-['Inter']">{key}</td>
                        <td className="px-3 py-2 text-right text-gray-900 font-['Inter'] font-medium">{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {onAction && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => onAction('export', data)}
                    className="px-3 py-1.5 bg-blue-600 text-white rounded text-[11px] font-['Inter'] hover:bg-blue-700 transition-colors"
                  >
                    Export Report
                  </button>
                  <button
                    onClick={() => onAction('compare', data)}
                    className="px-3 py-1.5 bg-white border border-blue-300 text-blue-700 rounded text-[11px] font-['Inter'] hover:bg-blue-50 transition-colors"
                  >
                    Compare Versions
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SuggestionMessage({ content, data, onAction }: { content?: string; data?: any; onAction?: (action: string, data: any) => void }) {
  return (
    <div className="flex items-start gap-3">
      <div className="bg-purple-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-semibold shrink-0">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      </div>
      <div className="flex-1">
        <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-3">
          <p className="text-[13px] text-purple-800 font-['Inter'] font-semibold mb-2">💡 Suggestion</p>
          <p className="text-[13px] text-purple-700 font-['Inter']">{content}</p>
          
          {onAction && data?.action && (
            <button
              onClick={() => onAction(data.action, data)}
              className="mt-3 px-3 py-1.5 bg-purple-600 text-white rounded text-[11px] font-['Inter'] hover:bg-purple-700 transition-colors"
            >
              {data.actionLabel || 'Apply Suggestion'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function SystemMessage({ content }: { content?: string }) {
  return (
    <div className="flex items-center justify-center">
      <div className="bg-gray-100 border border-gray-300 rounded-full px-4 py-1.5">
        <p className="text-[11px] text-gray-600 font-['Inter']">{content}</p>
      </div>
    </div>
  );
}

export default function ChatMessage({ message, onNodeClick, onAction }: ChatMessageProps) {
  const renderMessage = () => {
    switch (message.type) {
      case 'user':
        return <UserMessage content={message.content || ''} />;
      
      case 'ai-response':
        return <AIResponse content={message.content} metadata={message.metadata} />;
      
      case 'execution-trace':
        return <ExecutionTrace data={message.data} onNodeClick={onNodeClick} />;
      
      case 'intermediate-result':
        return <IntermediateResult data={message.data} metadata={message.metadata} />;
      
      case 'error':
        return <ErrorMessage content={message.content} data={message.data} />;
      
      case 'warning':
        return <WarningMessage content={message.content} />;
      
      case 'performance-report':
        return <PerformanceReport data={message.data} onAction={onAction} />;
      
      case 'suggestion':
        return <SuggestionMessage content={message.content} data={message.data} onAction={onAction} />;
      
      case 'system':
        return <SystemMessage content={message.content} />;
      
      default:
        return null;
    }
  };

  return (
    <div className="space-y-2">
      {renderMessage()}
    </div>
  );
}