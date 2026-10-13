import {useEffect,useState,type ChangeEvent} from 'react';
import {api,del,post,put} from './api';
import {Badge,PageTitle,useApi} from './components';
import type {Provider} from './types';
import './chat.css';

type MediaAsset={id:number;local_path:string;description?:string;ocr_text?:string};
type WebSource={title:string;url:string;snippet?:string};
type SentInfo={context:any[];attachments:string[];networkMode:string;sources:WebSource[]};

function fileName(path:string){return path.split(/[\\/]/).pop()||path}

export default function ChatPage(){
  const providers=useApi<Provider[]>('/ai/providers');
  const convs=useApi<any[]>('/ai/conversations');
  const media=useApi<MediaAsset[]>('/media');
  const[cid,setCid]=useState('');
  const[provider,setProvider]=useState('');
  const[model,setModel]=useState('');
  const[reasoning,setReasoning]=useState('自动');
  const[message,setMessage]=useState('');
  const[consent,setConsent]=useState(false);
  const[busy,setBusy]=useState(false);
  const[allowWeb,setAllowWeb]=useState(false);
  const[imageDetail,setImageDetail]=useState<'auto'|'low'|'high'>('low');
  const[selectedImages,setSelectedImages]=useState<number[]>([]);
  const[sent,setSent]=useState<SentInfo|null>(null);
  const chat=useApi<any>(cid?`/ai/conversations/${cid}`:null,[cid]);

  useEffect(()=>{if(providers.data?.length&&!provider)setProvider(providers.data[0].id)},[providers.data,provider]);
  const p=providers.data?.find(x=>x.id===provider);
  const modelInfo=p?.models?.find(x=>x.id===model);
  const canSendImages=modelInfo?.image_input==='verified_supported';
  const reasoningTests=modelInfo?.reasoning_tests||{};
  const reasoningOptions=['无',...['低','中','高','极高'].filter(level=>reasoningTests[level]!=='verified_unsupported'),'自动'];
  const canReason=modelInfo?.reasoning!=='verified_unsupported'||reasoningOptions.length>2;
  const nativeWeb=p?.protocol==='openai_responses'&&modelInfo?.web_search==='verified_supported';
  const imageAssets=(media.data||[]).filter(x=>/\.(png|jpe?g|webp)$/i.test(x.local_path));

  useEffect(()=>{
    if(!canSendImages)setSelectedImages([]);
    if(!canReason)setReasoning('无');
    else if(!reasoningOptions.includes(reasoning))setReasoning('自动');
    setConsent(false);
  },[provider,model,canSendImages,canReason,reasoningOptions.join('|'),reasoning]);

  function toggleImage(id:number){
    setConsent(false);
    setSelectedImages(current=>{
      if(current.includes(id))return current.filter(x=>x!==id);
      if(current.length>=4){alert('一次最多选择4张图片');return current}
      return [...current,id];
    });
  }

  async function uploadImage(event:ChangeEvent<HTMLInputElement>){
    const file=event.target.files?.[0];
    event.target.value='';
    if(!file)return;
    const body=new FormData();body.append('file',file);
    try{
      const result=await api<{id:number}>('/media/upload',{method:'POST',body});
      media.reload();setSelectedImages(ids=>[...ids,result.id].slice(-4));setConsent(false);
    }catch(error:any){alert(error.message)}
  }

  async function send(){
    setBusy(true);
    try{
      const result=await post<any>('/ai/chat',{
        conversation_id:cid||null,provider_id:provider,model,message,include_card:false,
        selected_note_ids:[],reasoning,max_output:1200,image_asset_ids:selectedImages,
        image_detail:imageDetail,allow_web:allowWeb,consent
      });
      setCid(result.conversation_id);
      setSent({context:result.sent_context||[],attachments:result.sent_attachments||[],networkMode:result.network_mode||'off',sources:result.web_sources||[]});
      setMessage('');setConsent(false);convs.reload();setTimeout(chat.reload,100);
    }catch(error:any){alert(error.message)}finally{setBusy(false)}
  }

  return <>
    <PageTitle title="AI 学习问答" kicker="SQLite 多轮会话 · 图片实传 · 可控联网" actions={<button onClick={()=>{setCid('');setSent(null)}}>＋ 新建会话</button>}/>
    <div className="ai-layout">
      <aside className="ai-controls">
        <h3>历史会话</h3>
        {convs.data?.map(x=><button className={cid===x.id?'active':''} key={x.id} onClick={()=>setCid(x.id)}>{x.title}</button>)}
        {cid&&<div className="row">
          <button onClick={async()=>{const title=prompt('新名称');if(title){await put(`/ai/conversations/${cid}`,{title});convs.reload()}}}>重命名</button>
          <button onClick={async()=>{const x=await post<any>(`/ai/conversations/${cid}/export`,{}).catch(()=>null);if(x)alert(x.path)}}>导出</button>
          <button className="danger" onClick={async()=>{if(confirm('删除会话及全部本地消息？')){await del(`/ai/conversations/${cid}`);setCid('');convs.reload()}}}>删除</button>
        </div>}
      </aside>
      <section className="chat-panel">
        <div className="messages">{chat.data?.messages?.map((x:any)=><article key={x.id} className={x.role}><Badge tone={x.role==='user'?'blue':'green'}>{x.role==='user'?'我':'AI'}</Badge><p>{x.content}</p></article>)}</div>
        {!cid&&<div className="ai-welcome"><b>λ</b><h2>开始一个可持续的学习会话</h2><p>网站自动携带摘要和最近消息；不会保存模型隐藏推理过程。</p></div>}
        {sent?.sources.length?<div className="web-sources"><h3>本次联网来源</h3>{sent.sources.map((source,index)=><a key={source.url} href={source.url} target="_blank" rel="noreferrer"><b>{index+1}. {source.title}</b>{source.snippet&&<span>{source.snippet}</span>}</a>)}</div>:null}
        <div className="prompt">
          <textarea value={message} onChange={e=>{setMessage(e.target.value);setConsent(false)}} placeholder="输入问题…"/>
          <details className="send-preview"><summary>发送前摘要</summary><p>服务商：{p?.display_name||'未选择'}；模型：{model||'未选择'}；历史：摘要和最近消息；图片：{selectedImages.length} 张；联网：{allowWeb?(nativeWeb?'服务商原生搜索':'本站后端公开网页检索'):'关闭'}。</p></details>
          <div><label><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>我已核对本次发送摘要</label><button disabled={busy||!message||!model||!p?.configured||!consent} onClick={send}>{busy?'生成中…':'发送'}</button></div>
        </div>
      </section>
      <aside className="ai-controls">
        <h3>本次任务</h3>
        <label>服务商<select value={provider} onChange={e=>{setProvider(e.target.value);setModel('')}}>{providers.data?.map(x=><option key={x.id} value={x.id}>{x.display_name}{x.configured?'':'（未配置）'}</option>)}</select></label>
        <label>模型<select value={model} onChange={e=>setModel(e.target.value)}><option value="">请选择</option>{p?.models?.map(x=><option key={x.id} value={x.id}>{x.id}</option>)}</select></label>
        {canReason&&<label>思考程度<select value={reasoning} onChange={e=>{setReasoning(e.target.value);setConsent(false)}}>{reasoningOptions.map(x=><option key={x}>{x}{reasoningTests[x]==='verified_supported'?'（已验证）':reasoningTests[x]==='test_failed'?'（测试失败）':''}</option>)}</select></label>}
        <label className="check-line"><input type="checkbox" checked={allowWeb} onChange={e=>{setAllowWeb(e.target.checked);setConsent(false)}}/>是否联网</label>
        <p className="muted">{allowWeb?(nativeWeb?'该模型已验证支持服务商原生网页搜索。':'该模型未验证原生搜索，本站后端将先检索公开网页，再把结果和来源交给模型。'):'关闭时不会为本次问题发起网页搜索。'}</p>
        <label>图片细节<select disabled={!canSendImages} value={imageDetail} onChange={e=>{setImageDetail(e.target.value as 'auto'|'low'|'high');setConsent(false)}}><option value="low">低（省费用）</option><option value="auto">自动</option><option value="high">高</option></select></label>
        <label className="file-button">上传并选择图片<input disabled={!canSendImages} type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" onChange={uploadImage}/></label>
        {!model?<p className="muted">先选择模型。</p>:!canSendImages?<p className="muted">该模型尚未通过图片输入测试，原图选择已禁用。</p>:<div className="image-picker">{imageAssets.length?imageAssets.map(asset=><label key={asset.id}><input type="checkbox" checked={selectedImages.includes(asset.id)} onChange={()=>toggleImage(asset.id)}/><span>{fileName(asset.local_path)}{asset.description?` · ${asset.description}`:''}</span></label>):<p className="muted">尚无 PNG/JPEG/WebP 图片，可在上方上传。</p>}</div>}
        <details><summary>查看上次实际发送上下文</summary><pre>{JSON.stringify(sent?{context:sent.context,attachments:sent.attachments,network_mode:sent.networkMode}:null,null,2)}</pre></details>
        <p className="muted">Responses 请求固定发送 <code>store:false</code>。图片与密钥均只由后端处理。</p>
      </aside>
    </div>
  </>
}
