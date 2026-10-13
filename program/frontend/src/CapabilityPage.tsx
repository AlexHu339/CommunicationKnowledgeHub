import {useEffect,useState} from 'react';
import {post,put} from './api';
import {PageTitle,useApi} from './components';
import type {Provider} from './types';

const tests=[
  ['text','文本对话'],['stream','流式输出'],['json','结构化 JSON'],['image','图片输入'],
  ['reasoning','思考程度'],['tools','工具调用'],['max_output','最大输出参数'],['web_search','原生联网搜索']
];

export default function CapabilityPage(){
  const providers=useApi<Provider[]>('/ai/providers');
  const[provider,setProvider]=useState('');
  const[model,setModel]=useState('');
  const[reasoning,setReasoning]=useState('极高');
  const[results,setResults]=useState<Record<string,any>>({});
  const[busy,setBusy]=useState('');
  useEffect(()=>{if(providers.data?.length&&!provider)setProvider(providers.data[0].id)},[providers.data,provider]);
  const current=providers.data?.find(x=>x.id===provider);

  async function run(capability:string){
    if(!current||!model)return;
    setBusy(capability);
    try{
      const result=await post<any>(`/ai/providers/${provider}/capability-test`,{model,capability,reasoning});
      setResults(value=>({...value,[capability]:result}));
      const field:Record<string,string>={text:'text_input',stream:'streaming',json:'structured_output',image:'image_input',reasoning:'reasoning',tools:'tool_calling',max_output:'max_output_test',web_search:'web_search'};
      const models=(current.models||[]).map(item=>{
        if(item.id!==model)return item;
        if(capability!=='reasoning')return {...item,[field[capability]]:result.status};
        const reasoningTests={...(item.reasoning_tests||{}),[reasoning]:result.status};
        const values=Object.values(reasoningTests);
        const overall=values.includes('verified_supported')?'verified_supported':values.length>=4&&values.every(x=>x==='verified_unsupported')?'verified_unsupported':'untested';
        return {...item,reasoning:overall,reasoning_tests:reasoningTests};
      });
      await put(`/ai/providers/${current.id}`,{id:current.id,display_name:current.display_name,protocol:current.protocol,base_url:current.base_url,api_key_env:current.api_key_env,models});
      providers.reload();
    }catch(error:any){alert(error.message)}finally{setBusy('')}
  }

  return <>
    <PageTitle title="模型能力独立测试" kicker="极短请求 · 调用前知情 · 结果持久保存"/>
    <div className="form-panel">
      <label>服务商<select value={provider} onChange={e=>{setProvider(e.target.value);setModel('');setResults({})}}>{providers.data?.map(x=><option key={x.id} value={x.id}>{x.display_name}</option>)}</select></label>
      <label>模型<select value={model} onChange={e=>{setModel(e.target.value);setResults({})}}><option value="">请选择</option>{current?.models?.map(x=><option key={x.id} value={x.id}>{x.id}</option>)}</select></label>
      <label>思考程度测试档位<select value={reasoning} onChange={e=>setReasoning(e.target.value)}>{['低','中','高','极高'].map(x=><option key={x}>{x}{current?.models?.find(item=>item.id===model)?.reasoning_tests?.[x]?`（${current.models.find(item=>item.id===model)?.reasoning_tests?.[x]}）`:''}</option>)}</select></label>
      <div className="notice">以下测试会产生极少量 API 费用；“原生联网搜索”测试可能产生服务商搜索工具费用。图片测试只发送程序内置 1×1 测试图，不发送用户图片。</div>
      <div className="diag">{tests.map(([capability,name])=>{const result=results[capability];return <article key={capability} className={result?.status==='verified_supported'?'pass':result?'fail':''}><div><h3>{name}</h3><p>{result?.status||'未测试'}{result?.http_status?` · HTTP ${result.http_status}`:''}</p>{result?.detail&&<small>{result.detail}</small>}</div><button disabled={!model||!!busy} onClick={()=>run(capability)}>{busy===capability?'测试中…':'开始短测试'}</button></article>})}</div>
    </div>
  </>
}
