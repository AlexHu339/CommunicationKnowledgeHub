import React from'react';
import{createRoot}from'react-dom/client';
import{BrowserRouter}from'react-router-dom';
import App from'./App';
import'./styles.css';
import'katex/dist/katex.min.css';

class RootErrorBoundary extends React.Component<React.PropsWithChildren<object>,{error:Error|null}>{
  state={error:null as Error|null};
  static getDerivedStateFromError(error:Error){return{error}}
  componentDidCatch(error:Error,info:React.ErrorInfo){console.error('页面渲染失败',error,info)}
  render(){return this.state.error?<main style={{maxWidth:760,margin:'8vh auto',padding:32,color:'#17352c',background:'linear-gradient(135deg,#fff,#eaf9ec)',border:'1px solid #cbe2d1',borderRadius:18}}><h1>页面加载失败</h1><p>前端缓存或页面组件发生异常。请点击下面按钮重新载入最新版本。</p><pre style={{whiteSpace:'pre-wrap',color:'#a62f45'}}>{this.state.error.message}</pre><button onClick={()=>location.reload()}>重新载入</button></main>:this.props.children}
}

async function boot(){
  try{const h=await fetch('/api/health').then(r=>r.json());if(!h.setup_complete&&location.pathname==='/')history.replaceState(null,'','/setup')}catch{}
  createRoot(document.getElementById('root')!).render(<React.StrictMode><RootErrorBoundary><BrowserRouter><App/></BrowserRouter></RootErrorBoundary></React.StrictMode>)
}

boot();
if('serviceWorker'in navigator)window.addEventListener('load',async()=>{
  try{
    const registration=await navigator.serviceWorker.register('/sw.js');
    await registration.update();
  }catch(error){console.warn('PWA 更新检查失败',error)}
});
