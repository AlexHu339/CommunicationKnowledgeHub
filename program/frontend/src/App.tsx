import {useEffect,useState} from 'react';
import {NavLink,Route,Routes,useLocation} from 'react-router-dom';
import {api,saveToken} from './api';
import CapabilityPage from './CapabilityPage';
import DataPage from './DataPage';
import {
  AiConfig,Backups,CardDetail,Dashboard,Diagnostics,ExternalAiLinks,FavoritesNotes,
  GenerateKnowledge,KnowledgeMap,MediaManager,NetworkUpdates,OcrPage,Policies,
  PostgradBasics,ReviewCenter,ReviewQueue,SearchPage,Settings,SetupWizard,
  Statistics,SubjectCenter,Today,Universities,Usage,
} from './pages';

const nav=[
  ['总览','/','◈'],['今日认识8个','/today','✦'],['学科知识地图','/map','⌘'],
  ['复习中心','/review','↻'],['收藏与笔记','/notes','☆'],['电赛中心','/competition','⚡'],
  ['仪器与模块','/instruments','⌁'],['考研常识','/postgrad','研'],['政策时间线','/policies','时'],
  ['院校比较','/universities','校'],['AI网页入口','/ai-links','↗'],['图片与OCR','/ocr','◎'],
  ['DeepSeek扩充知识','/generate','＋'],['网络更新','/updates','↯'],['内容审核','/review-queue','✓'],
  ['图片与来源','/media','▣'],['学习统计','/statistics','▥'],['设置','/settings','⚙'],
  ['API服务配置','/ai-config','钥'],['模型能力测试','/capabilities','验'],['费用统计','/usage','￥'],
  ['数据导入导出','/data','⇄'],['备份恢复','/backups','⇩'],['系统诊断','/diagnostics','诊'],
] as const;

function DynamicBackground(){
  return <div className="dynamic-sky" aria-hidden="true">
    <div className="blue-sky-scene"/>
    <div className="drifting-cloud cloud-near"/><div className="drifting-cloud cloud-far"/>
    <div className="water-shimmer"/><div className="sky-reading-shade"/>
  </div>;
}

export default function App(){
  const[collapsed,setCollapsed]=useState(false);
  const[search,setSearch]=useState('');
  const[health,setHealth]=useState<any>(null);
  const[login,setLogin]=useState(false);
  const loc=useLocation();
  useEffect(()=>{api<any>('/health').then(h=>{setHealth(h);if(h.mode==='lan')api('/dashboard').catch((e:any)=>e.status===401&&setLogin(true))}).catch(()=>{})},[]);
  useEffect(()=>{document.documentElement.scrollTop=0;document.body.scrollTop=0;const shell=document.querySelector('.shell');if(shell instanceof HTMLElement)shell.scrollTop=0},[loc.pathname]);
  if(login)return <><DynamicBackground/><Login onDone={()=>setLogin(false)}/></>;
  return <><DynamicBackground/><div className={`app ${collapsed?'collapsed':''}`}>
    <aside><div className="brand"><div className="brandmark">λ</div><div><b>通信知识枢纽</b><small>LOCAL · v1.0</small></div></div>
      <nav>{nav.map(([name,path,icon])=><NavLink key={path} to={path} end={path==='/' } title={name}><i>{icon}</i><span>{name}</span></NavLink>)}</nav>
      <button className="collapse" onClick={()=>setCollapsed(x=>!x)}>{collapsed?'›':'‹ 收起导航'}</button>
    </aside>
    <div className="shell"><header className="topbar"><button className="mobile-menu" onClick={()=>setCollapsed(x=>!x)}>☰</button>
      <form onSubmit={event=>{event.preventDefault();location.href=`/search?q=${encodeURIComponent(search)}`}}><span>⌕</span><input value={search} onChange={event=>setSearch(event.target.value)} placeholder="搜索知识点、笔记、政策或院校…"/></form>
      <div className="runtime"><span className={`dot ${health?'ok':''}`}/>{health?`${health.mode==='local'?'本机免登录':'局域网'} · ${health.cards}个知识主题`:'后端连接中'}</div>
    </header><main><Routes>
      <Route path="/" element={<Dashboard/>}/><Route path="/today" element={<Today/>}/><Route path="/map" element={<KnowledgeMap/>}/><Route path="/graph" element={<KnowledgeMap/>}/><Route path="/cards/:id" element={<CardDetail/>}/>
      <Route path="/review" element={<ReviewCenter/>}/><Route path="/notes" element={<FavoritesNotes/>}/><Route path="/competition" element={<SubjectCenter subject="电赛知识" title="电赛中心"/>}/><Route path="/instruments" element={<SubjectCenter subject="工程通识与仪器使用" title="仪器与模块中心"/>}/>
      <Route path="/postgrad" element={<PostgradBasics/>}/><Route path="/policies" element={<Policies/>}/><Route path="/universities" element={<Universities/>}/>
      <Route path="/ai" element={<ExternalAiLinks/>}/><Route path="/ai-links" element={<ExternalAiLinks/>}/><Route path="/ocr" element={<OcrPage/>}/><Route path="/generate" element={<GenerateKnowledge/>}/>
      <Route path="/updates" element={<NetworkUpdates/>}/><Route path="/review-queue" element={<ReviewQueue/>}/><Route path="/media" element={<MediaManager/>}/><Route path="/statistics" element={<Statistics/>}/>
      <Route path="/settings" element={<Settings/>}/><Route path="/ai-config" element={<AiConfig/>}/><Route path="/capabilities" element={<CapabilityPage/>}/><Route path="/usage" element={<Usage/>}/><Route path="/data" element={<DataPage/>}/><Route path="/backups" element={<Backups/>}/><Route path="/diagnostics" element={<Diagnostics/>}/><Route path="/setup" element={<SetupWizard/>}/><Route path="/search" element={<SearchPage/>}/>
    </Routes></main></div>
  </div></>;
}

function Login({onDone}:{onDone:()=>void}){
  const[user,setUser]=useState('learner'),[password,setPassword]=useState(''),[error,setError]=useState('');
  return <div className="login"><form onSubmit={async event=>{event.preventDefault();try{const result=await api<any>('/auth/login',{method:'POST',body:JSON.stringify({username:user,password})});saveToken(result.token);onDone()}catch(reason:any){setError(reason.message)}}}>
    <div className="brandmark">λ</div><h1>局域网安全登录</h1><p>本机访问免登录，其他设备必须验证。</p>{error&&<div className="error">{error}</div>}
    <label>用户名<input value={user} onChange={event=>setUser(event.target.value)}/></label><label>密码<input type="password" value={password} onChange={event=>setPassword(event.target.value)}/></label><button type="submit">登录</button>
  </form></div>;
}
