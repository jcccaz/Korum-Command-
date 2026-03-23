import React, { useState, useEffect } from 'react';

const SPARKLINE_BARS = " ▂▃▄▅▆▇█";

function generateSparkline(data) {
  const max = Math.max(...data);
  return data.map(v => SPARKLINE_BARS[Math.floor((v / max) * 7)]).join('');
}

function App() {
  const [ledgerFeed, setLedgerFeed] = useState([]);
  const [retriesCost, setRetriesCost] = useState(0);
  const [apiVariableCost, setApiVariableCost] = useState(0);
  const [vendorCosts, setVendorCosts] = useState({
    OPENAI: 0, ANTHROPIC: 0, GEMINI: 0, PERPLEXITY: 0, MISTRAL: 0
  });
  const [falconBlocks, setFalconBlocks] = useState({ pii: 0, inject: 0, json: 0 });
  const [sysTime, setSysTime] = useState(new Date().toISOString());
  const [cmdInput, setCmdInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [devHealth, setDevHealth] = useState({
    avg_latency_ms: 0,
    failed_missions_24h: 0,
    engine_version: "V3.1"
  });

  // 24H burn array (retaining sparkline visual structure until timeseries API built)
  const [burnRateData] = useState(Array.from({ length: 48 }, () => Math.random() * 5 + 0.5));

  useEffect(() => {
    const t = setInterval(() => setSysTime(new Date().toISOString()), 50);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const res = await fetch('http://127.0.0.1:5000/api/cost_command/live');
        if (!res.ok) throw new Error("Status " + res.status);
        const data = await res.json();
        
        if (data.success) {
          setIsConnected(true);
          setLedgerFeed(data.ledger_feed);
          setRetriesCost(data.wasted_capital);
          setApiVariableCost(data.total_variable_cost);
          setVendorCosts(d => ({ ...d, ...data.vendors }));
          if (data.falcon) setFalconBlocks(data.falcon);
          if (data.dev_health) setDevHealth(data.dev_health);
        }
      } catch (err) {
        setIsConnected(false);
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2500); // 2.5s Sync Loop
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen w-screen bg-black text-[#A0A0A0] font-mono flex flex-col p-2 text-xs md:text-sm selection:bg-[#00FF41] selection:text-black">
      
      {/* Top Bar */}
      <div className="flex justify-between border border-[#333] p-1.5 mb-1 bg-[#050505]">
        <span className="flex items-center gap-2">
          KORUM // NODE: ALPHA-7 // STATUS: <span className={isConnected ? "text-[#00FF41] mt-[1px]" : "text-[#FF3131] mt-[1px]"}>●</span> // {sysTime}
        </span>
        <span className="hidden md:inline">OP-MODE: TACTICAL FINANCIAL</span>
      </div>

      <div className="flex-1 flex flex-col md:flex-row gap-1 overflow-hidden">
        
        {/* Left Rail (40%) */}
        <div className="w-full md:w-[40%] flex flex-col border border-[#333] p-4 bg-[#050505] overflow-y-auto">
          
          <h2 className="text-white mb-2 font-bold tracking-widest">[{'>'} TOTAL CAPITAL DRAW (24H)]</h2>
          <div className="text-4xl text-[#00FF41] font-bold mb-4">${(apiVariableCost + 15.10).toFixed(2)}</div>

          <div className="mb-8 space-y-1.5 text-xs">
             <div className="flex justify-between border-b border-[#222] pb-1">
               <span className="text-[#777]">API.VARIABLE (LLMs):</span> <span className="text-white">${apiVariableCost.toFixed(2)}</span>
             </div>
             <div className="flex justify-between border-b border-[#222] pb-1">
               <span className="text-[#777]">STATIC.INFRASTRUCTURE:</span> <span className="text-white">$15.10</span>
             </div>
             <div className="flex justify-between border-b border-[#222] pb-1 mt-2">
               <span className="text-[#FF3131]">WASTED CAPITAL (RETRIES):</span> <span className="text-[#FF3131]">-${retriesCost.toFixed(2)}</span>
             </div>
          </div>

          <div className="mb-8">
             <div className="text-[#777] mb-2 uppercase text-xs">BURN RATE (LAST 24H)</div>
             <div className="text-[#00FF41] tracking-widest text-lg leading-none overflow-hidden whitespace-nowrap opacity-80">
               {generateSparkline(burnRateData)}
             </div>
             <div className="text-[#777] mt-1.5 flex justify-between text-[9px] uppercase tracking-widest">
                <span>R-INDEX: {ledgerFeed.length ? (((ledgerFeed.length - (retriesCost/0.05)) / ledgerFeed.length) * 100).toFixed(1) : "100"}%</span>
                <span>VOL_CAP: NOMINAL</span>
             </div>
          </div>

          <h2 className="text-white mb-2 font-bold tracking-widest">[{'>'} KORUM ENGINE (RUNTIME API)]</h2>
          <ul className="mb-6 space-y-1.5 text-xs">
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#777]">OPENAI:</span> <span className="text-white">${(vendorCosts.OPENAI || 0).toFixed(4)}</span></li>
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#777]">CLAUDE (ANTHROPIC):</span> <span className="text-white">${(vendorCosts.ANTHROPIC || 0).toFixed(4)}</span></li>
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#777]">GEMINI:</span> <span className="text-white">${(vendorCosts.GEMINI || 0).toFixed(4)}</span></li>
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#777]">PERPLEXITY:</span> <span className="text-white">${(vendorCosts.PERPLEXITY || 0).toFixed(4)}</span></li>
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#777]">MISTRAL:</span> <span className="text-white">${(vendorCosts.MISTRAL || 0).toFixed(4)}</span></li>
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#777]">SERPAPI (OSINT):</span> <span className="text-[#FFBF00]">${(vendorCosts.SERPAPI || 0).toFixed(4)}</span></li>
          </ul>

          <h2 className="text-white mb-2 font-bold tracking-widest">[{'>'} DEVELOPMENT ENGINE]</h2>
          <ul className="mb-6 space-y-1.5 text-xs">
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#FFBF00]">ANTIGRAVITY (BUILD OUTLIER):</span> <span className="text-[#FFBF00]">$0.00 (PENDING SYNC)</span></li>
          </ul>

          <h2 className="text-white mb-2 font-bold tracking-widest">[{'>'} INFRASTRUCTURE]</h2>
          <ul className="mb-6 space-y-1.5 text-xs">
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#777]">AWS (S3/EC2):</span> <span className="text-white">$3.10</span></li>
             <li className="flex justify-between border-b border-[#222] pb-1"><span className="text-[#777]">RAILWAY:</span> <span className="text-white">$12.00</span></li>
          </ul>

          <h2 className="text-white mb-2 font-bold tracking-widest">[{'>'} FALCON SHIELD DISTRIBUTION]</h2>
          <ul className="mb-8 space-y-1.5 text-xs">
             <li className="flex justify-between border-b border-[#222] pb-1">
               <span className="text-[#777]">PII_REDACT:</span> <span className="text-white">{falconBlocks.pii}</span>
             </li>
             <li className="flex justify-between border-b border-[#222] pb-1">
               <span className="text-[#777]">PROMPT_INJECT:</span> <span className="text-white">{falconBlocks.inject}</span>
             </li>
             <li className="flex justify-between border-b border-[#222] pb-1">
               <span className="text-[#777]">MALFORMED_JSON:</span> <span className="text-white">{falconBlocks.json}</span>
             </li>
          </ul>
          
          <div className="mt-auto">
            <h2 className="text-white mb-1 text-[10px] tracking-widest uppercase">[{'>'} ACTIVE DEBIT ROUTE]</h2>
            <div className="text-[#00FF41] font-bold tracking-widest text-xs">
              CREDIT-01 [AUTHORIZED]
            </div>
          </div>
          
        </div>

        {/* Center (60%) */}
        <div className="w-full md:w-[60%] flex flex-col gap-1">
          
          {/* Top Half: KPIs */}
          <div className="flex flex-col xl:flex-row gap-1 flex-1">
             
             {/* Dev Health Tracking */}
             <div className="flex-1 border border-[#333] bg-[#050505] p-5 flex flex-col">
               <h2 className="text-white mb-6 font-bold tracking-widest">[{'>'} DEVELOPMENT HEALTH]</h2>
               <div className="grid grid-cols-2 gap-6 mb-4">
                  <div>
                    <div className="text-[#777] text-[10px] uppercase tracking-widest mb-1">SYSTEM UPTIME (30D)</div>
                    <div className="text-[#A0A0A0] text-3xl font-bold">AWAITING CI/CD PROBE</div>
                  </div>
                  <div>
                    <div className="text-[#777] text-[10px] uppercase tracking-widest mb-1">AVG API LATENCY</div>
                    <div className="text-white text-3xl font-bold">{devHealth.avg_latency_ms}ms</div>
                  </div>
                  <div>
                    <div className="text-[#777] text-[10px] uppercase tracking-widest mb-1">FAILED MISSIONS (24h)</div>
                    <div className={devHealth.failed_missions_24h > 0 ? "text-[#FF3131] text-3xl font-bold" : "text-[#00FF41] text-3xl font-bold"}>{devHealth.failed_missions_24h}</div>
                  </div>
                  <div>
                    <div className="text-[#777] text-[10px] uppercase tracking-widest mb-1">CORE ENGINE VERSION</div>
                    <div className="text-white text-3xl font-bold">{devHealth.engine_version}</div>
                  </div>
               </div>
               
               <div className="mt-auto">
                 <h3 className="text-[#777] text-[10px] uppercase border-[#222] border-t pt-2 tracking-widest">
                   LAST DEPLOYMENT: <span className="text-[#FFBF00]">AWAITING INFRA KEY</span>
                 </h3>
               </div>
             </div>

             {/* Financial Budget Trajectory */}
             <div className="flex-1 border border-[#333] bg-[#050505] p-5 flex flex-col">
               <h2 className="text-white mb-6 font-bold tracking-widest">[{'>'} BUDGET TRAJECTORY]</h2>
               
               <div className="mb-8">
                 <div className="flex justify-between text-[10px] text-[#777] mb-2 tracking-widest">
                    <span>MARCH ALLOWANCE EXHAUSTION</span>
                    <span className="text-white">$142.50 / $250.00</span>
                 </div>
                 <div className="w-full bg-[#111] h-4">
                    <div className="bg-[#FFBF00] h-full transition-all" style={{ width: '57%' }}></div>
                 </div>
               </div>

               <div className="mt-auto space-y-3 text-xs tracking-widest">
                 <div className="flex justify-between border-b border-[#222] pb-1.5">
                   <span className="text-[#777]">PROJECTED MONTLY END:</span>
                   <span className="text-[#FFBF00]">$210.45</span>
                 </div>
                 <div className="flex justify-between border-b border-[#222] pb-1.5">
                   <span className="text-[#777]">VARIANCE TO BUDGET CAP:</span>
                   <span className="text-[#00FF41]">+$39.55 SAF</span>
                 </div>
                 <div className="flex justify-between border-b border-[#222] pb-1.5">
                   <span className="text-[#777]">LAST INVOICE CYCLE:</span>
                   <span className="text-white">MAR-01 RUN</span>
                 </div>
               </div>
             </div>
          </div>

          {/* Bottom Half: Raw Event Stream constrained */}
          <div className="h-[260px] border border-[#333] bg-black relative flex flex-col">
            <div className="absolute top-0 left-0 w-full p-2 border-b border-[#333] bg-[#111] z-10 flex justify-between items-center">
               <span className="text-white tracking-widest font-bold">[{'>'} RAW EVENT AUDIT LOG]</span>
               <span className="text-[#00FF41] text-[10px] tracking-widest animate-pulse flex items-center gap-2">
                 <span className="h-2 w-2 bg-[#00FF41] rounded-full inline-block"></span> 5173_WS
               </span>
            </div>
            <div className="flex-1 overflow-y-auto mt-10 p-3 flex flex-col-reverse gap-0.5 text-[10px]">
               {ledgerFeed.map((entry, idx) => (
                  <div key={idx} className={`whitespace-pre-wrap tracking-wide ${entry.isRetry ? 'text-[#FF3131] bg-[#FF3131]/10 px-1' : 'text-[#777] hover:text-[#E0E0E0] hover:bg-[#111] px-1'}`}>
                     {entry.timestamp.split('T')[1].replace('Z','')} | {entry.mission_id} | {entry.hash} | COST: ${entry.cost.toFixed(4)} | {entry.provider}:{entry.model} {entry.isRetry && '<< ABORT CAUGHT >>'}
                  </div>
               ))}
               {ledgerFeed.length === 0 && <div className="text-[#444] animate-pulse">AWAITING CONNECTION...</div>}
            </div>
          </div>
        </div>
        
      </div>

      {/* Footer */}
      <div className="border border-[#333] p-1.5 mt-1 bg-[#111] flex items-center text-white">
        <span className="mr-2 px-1 text-[#00FF41]">[ CMD {'>'}</span>
        <input 
          autoFocus 
          className="bg-transparent outline-none flex-1 font-mono text-white caret-[#00FF41]" 
          type="text" 
          value={cmdInput}
          onChange={(e) => setCmdInput(e.target.value)}
          spellCheck="false"
        />
        <span className="text-[#00FF41]">]</span>
      </div>
      
    </div>
  );
}

export default App;
