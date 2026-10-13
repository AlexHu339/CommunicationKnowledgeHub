import{useEffect,useState}from'react';import{Link,useParams,useSearchParams}from'react-router-dom';import ReactMarkdown from'react-markdown';import remarkMath from'remark-math';import rehypeKatex from'rehype-katex';import{api,del,post,put}from'./api';import{Badge,CardGrid,EChart,ErrorBox,Loading,PageTitle,Stat,useApi}from'./components';import type{Card,Note,Provider}from'./types';

export function Dashboard(){
  const d=useApi<any>('/dashboard'),cards=useApi<Card[]>('/cards?mode=new&limit=4');
  if(d.error)return <ErrorBox error={d.error}/>;
  return <><PageTitle title="今天，先真正弄懂一个概念" kicker="通信工程 · 本地知识库" actions={<Link className="button primary" to="/today">开始认识 8 个 →</Link>}/>
    <section className="hero"><div><Badge tone="green">本地知识库 · 学习记录保存在电脑</Badge><h2>把抽象名词，<em>讲成能看懂、能想象、能使用的知识。</em></h2><p>先用一小段话建立直观认识，再阅读完整解释；只有确实需要时才展开公式、例子或工程场景。</p></div><div className="signal-art"><svg viewBox="0 0 480 180"><path d="M0 90 C30 15 60 15 90 90 S150 165 180 90 240 15 270 90 330 165 360 90 420 15 480 90"/><path className="faint" d="M0 90H480M0 45H480M0 135H480"/></svg></div></section>
    {d.data?<div className="stats"><Stat label="知识主题" value={d.data.cards}/><Stat label="已接触" value={d.data.viewed} sub={'掌握 '+d.data.mastered}/><Stat label="今日待复习" value={d.data.reviews_due}/><Stat label="收藏" value={d.data.favorites}/><Stat label="待确认内容" value={d.data.pending}/></div>:<Loading/>}
    <section className="section-head"><div><span className="kicker">NEXT UP</span><h2>为你挑选的下一组知识</h2></div><Link to="/map">浏览全部学科 →</Link></section>{cards.data?<CardGrid cards={cards.data}/>:cards.error?<ErrorBox error={cards.error}/>:<Loading/>}
  </>;
}

export function KnowledgeMap(){const subjects=useApi<{name:string;count:number}[]>('/subjects'),[selected,setSelected]=useState(''),cards=useApi<Card[]>(selected?`/cards?subject=${encodeURIComponent(selected)}&mode=random&limit=8`:null,[selected]);return <><PageTitle title="学科知识地图" kicker="16 门领域 · 可持续扩展"/><div className="subject-grid">{subjects.data?.map((s,i)=><button key={s.name} className={selected===s.name?'selected':''} onClick={()=>setSelected(s.name)}><i>{String(i+1).padStart(2,'0')}</i><b>{s.name}</b><span>{s.count} 个知识点</span></button>)}</div>{selected&&<><div className="section-head"><h2>{selected}</h2><button onClick={cards.reload}>换一批（仅本地）</button></div>{cards.data?<CardGrid cards={cards.data}/>:<Loading/>}</>}</>}

export function CardDetail(){
  const{id}=useParams(),c=useApi<Card>(id?'/cards/'+id:null,[id]),[note,setNote]=useState('');
  useEffect(()=>{if(id)put('/cards/'+id+'/state',{viewed:true}).catch(()=>{})},[id]);
  if(c.error)return <ErrorBox error={c.error}/>;
  if(!c.data)return <Loading/>;
  const x=c.data,hasRewrite=Boolean(x.explanation?.trim());
  const legacy=[x.why_exists,x.problem_solved,x.intuition,x.common_uses,x.simple_example].filter(value=>value?.trim()).join('\n\n');
  return <><PageTitle title={x.title} kicker={x.subject+' · '+x.chapter}/>
    <div className="detail-layout"><article className="detail natural-detail">
      <section className="thirty"><Badge>先认识一下</Badge><ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{x.summary}</ReactMarkdown></section>
      <section className="article-body">
        {!hasRewrite&&<div className="rewrite-pending">这个主题仍在等待通俗内容重写，下面暂时显示旧版说明。</div>}
        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{hasRewrite?x.explanation!:legacy}</ReactMarkdown>
      </section>
      {x.sections?.map(section=><section className="optional-section" key={section.heading}><h3>{section.heading}</h3><ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{section.content}</ReactMarkdown></section>)}
      {Boolean(x.accuracy_notes?.length)&&<section className="accuracy-notes"><h3>需要留意</h3>{x.accuracy_notes!.map(item=><p key={item}>{item}</p>)}</section>}
      <details className="source-detail"><summary>内容来源与版本</summary><p>{x.source}</p><p>内容版本：{x.content_version}</p></details>
    </article><aside className="note-panel"><h3>个人笔记</h3>{x.notes?.map(n=><div className="note" key={n.id}><b>{n.title}</b><p>{n.content}</p></div>)}<textarea value={note} onChange={event=>setNote(event.target.value)} placeholder="记录自己的理解、疑问或实验现象…"/><button onClick={async()=>{if(!note.trim())return;await post('/notes',{card_id:x.id,title:x.title+'笔记',content:note});setNote('');c.reload()}}>保存到 SQLite</button></aside></div>
  </>;
}


export function Today(){
  const[mode,setMode]=useState('new'),[nonce,setNonce]=useState(0),r=useApi<Card[]>('/cards?mode='+mode+'&limit=8&batch='+nonce,[mode,nonce]);
  return <><PageTitle title="今日认识 8 个" actions={<><select value={mode} onChange={event=>setMode(event.target.value)}><option value="new">认识新知识</option><option value="consolidate">巩固旧知识</option><option value="review">待复习</option><option value="competition">电赛优先</option><option value="random">完全随机</option></select><button onClick={()=>{setNonce(x=>x+1);r.reload()}}>换一批（本地）</button><Link className="button ghost" to="/generate">用 DeepSeek 扩充知识</Link></>}/>
    <div className="notice compact-notice">“换一批”只从本地知识库选择，不产生API费用；只有“用 DeepSeek 扩充知识”会调用你配置的模型，新内容会先进入内容审核。</div>
    {r.data?.length?<CardGrid cards={r.data}/>:r.data?<div className="empty">当前模式没有待选主题，可切换模式。</div>:<Loading/>}
  </>;
}
export function ReviewCenter(){const r=useApi<Card[]>('/cards?mode=review&limit=40');return <><PageTitle title="复习中心" kicker="状态 + 上次浏览 + 手动日期"/>{r.data?.length?<CardGrid cards={r.data} onChanged={r.reload}/>:r.data?<div className="empty">目前没有到期复习项目。</div>:<Loading/>}</>}

export function FavoritesNotes(){const notes=useApi<Note[]>('/notes'),cards=useApi<Card[]>('/cards?mode=favorites&limit=100');return <><PageTitle title="收藏与笔记"/><h2>收藏的知识卡</h2>{cards.data?<CardGrid cards={cards.data} onChanged={cards.reload}/>:<Loading/>}<div className="section-head"><h2>全部笔记</h2></div><div className="note-list">{notes.data?.map(n=><article key={n.id}><div><b>{n.title}</b><p>{n.content}</p></div><button onClick={async()=>{if(confirm('确定删除这条笔记？')){await del(`/notes/${n.id}`);notes.reload()}}}>删除</button></article>)}</div></>}
export function SubjectCenter({subject,title}:{subject:string;title:string}){const r=useApi<Card[]>(`/cards?subject=${encodeURIComponent(subject)}&mode=random&limit=40`);return <><PageTitle title={title} kicker={subject==='电赛知识'?'从指标拆解到联调答辩':'测量可信，结论才可信'}/>{r.data?<CardGrid cards={r.data}/>:<Loading/>}</>}
export function PostgradBasics(){
  const r=useApi<Card[]>('/cards?subject=考研常识&mode=random&limit=60');
  return <><PageTitle title="2028 年硕士入学 · 考研常识" kicker="用完整句子讲清概念和实际流程"/><div className="notice">考研常识不再套用“输入、输出”等工程模板。动态政策、分数线和招生人数必须以对应年份官方原文为准。</div>{r.data?<CardGrid cards={r.data}/>:<Loading/>}</>;
}

export function Policies(){const r=useApi<any[]>('/policies');return <><PageTitle title="政策时间线"/>{r.data?.length?<div className="timeline">{r.data.map(p=><article key={p.id}><time>{p.published_date||'日期待核实'}</time><div><Badge tone="green">{p.institution}</Badge><h2>{p.title}</h2><details><summary>查看官方原文</summary><p>{p.original_text}</p><a href={p.source_url} target="_blank">打开官方来源</a></details><details><summary>AI 解释（独立显示）</summary><p>{p.ai_explanation||'尚未调用 AI 解释'}</p></details></div></article>)}</div>:r.data?<div className="empty">尚无已审核政策。请在“网络更新”检查官方来源，新内容会先进入待审核中心。</div>:<Loading/>}</>}
export function Universities(){const r=useApi<any[]>('/universities'),[selected,setSelected]=useState<number[]>([]);const rows=(r.data||[]).filter(x=>selected.includes(x.id));return <><PageTitle title="院校搜索与比较" kicker="可并排比较 2—6 所"/><div className="university-picker">{r.data?.map(x=><label key={x.id}><input type="checkbox" checked={selected.includes(x.id)} disabled={!selected.includes(x.id)&&selected.length>=6} onChange={()=>setSelected(s=>s.includes(x.id)?s.filter(i=>i!==x.id):[...s,x.id])}/><b>{x.school}</b><span>{x.province} · {x.program_name}</span></label>)}</div>{rows.length>0&&<div className="compare"><table><thead><tr><th>字段</th>{rows.map(x=><th key={x.id}>{x.school}</th>)}</tr></thead><tbody>{[['学院','college'],['专业代码','program_code'],['专业名称','program_name'],['学硕/专硕','degree_type'],['初试科目','exam_subjects'],['数学','math_type'],['英语','english_type'],['专业课','professional_exam'],['参考书','reference_books'],['招生计划','enrollment_plan'],['统考名额','unified_exam_slots'],['复试线','retest_line'],['学制','duration'],['学费','tuition'],['缺失项','missing_fields']].map(([label,key])=><tr key={key}><th>{label}</th>{rows.map(x=><td key={x.id}>{x[key]||'未找到或待核实'}</td>)}</tr>)}</tbody></table></div>}</>}

export function ExternalAiLinks(){
  return <><PageTitle title="常用 AI 网页" kicker="站内不再保存聊天；需要问答时直接打开官方网页"/>
    <div className="external-ai-grid">
      <a href="https://chatgpt.com/" target="_blank" rel="noreferrer"><span className="external-logo">GPT</span><div><h2>ChatGPT 官方网页</h2><p>适合继续提问、图片理解和综合分析。</p><b>打开 chatgpt.com ↗</b></div></a>
      <a href="https://chat.deepseek.com/" target="_blank" rel="noreferrer"><span className="external-logo deepseek-logo">DS</span><div><h2>DeepSeek 官方网页</h2><p>适合中文概念解释、推理和内容整理。</p><b>打开 DeepSeek ↗</b></div></a>
    </div>
    <div className="notice">这里的网页链接与本站API配置彼此独立。本站仍保留DeepSeek API，用于生成新的知识候选；日常“换一批”不会调用API。</div>
  </>;
}

export function OcrPage(){
  const[file,setFile]=useState<File|null>(null),[asset,setAsset]=useState<number|null>(null),[text,setText]=useState(''),[busy,setBusy]=useState(false);
  return <><PageTitle title="图片与 OCR" kicker="PaddleOCR CPU · 本地处理 · 无需 API Key"/><div className="notice compact-notice">这个功能与站内AI聊天无关，适合提取教材、考研公告、报错截图、仪器屏幕和扫描PDF中的文字。识别结果先留在本机，由你决定是否复制到外部AI。</div>
    <div className="upload-zone"><b>上传截图、图片或 PDF</b><p>PDF 优先提取原始文字；扫描件再走 OCR。单文件上限 20 MB。</p><input type="file" accept="image/png,image/jpeg,image/webp,image/bmp,application/pdf" onChange={event=>setFile(event.target.files?.[0]||null)}/><button disabled={!file||busy} onClick={async()=>{setBusy(true);try{const form=new FormData();form.append('file',file!);const uploaded=await api<any>('/media/upload',{method:'POST',body:form});setAsset(uploaded.id);const result=await post<any>('/media/'+uploaded.id+'/ocr',{});setText(result.text)}catch(error:any){setText('处理失败：'+error.message)}finally{setBusy(false)}}}>{busy?'本地识别中…':'上传并执行本地 OCR'}</button></div>
    {asset&&<section className="panel"><div className="section-head"><h2>可编辑识别结果</h2><Badge tone="green">只在本机处理</Badge></div><textarea className="ocr-text" value={text} onChange={event=>setText(event.target.value)}/><p className="muted">可检查并修改识别错误，再自行复制到ChatGPT或DeepSeek。</p></section>}
  </>;
}

export function GenerateKnowledge(){
  const providers=useApi<Provider[]>('/ai/providers'),[subject,setSubject]=useState('通信原理'),[topic,setTopic]=useState(''),[provider,setProvider]=useState('deepseek'),[model,setModel]=useState(''),[result,setResult]=useState('');
  useEffect(()=>{if(providers.data?.length&&!providers.data.some(item=>item.id===provider))setProvider(providers.data[0].id)},[providers.data]);
  const selected=providers.data?.find(item=>item.id===provider);
  return <><PageTitle title="用 DeepSeek 扩充知识" kicker="生成的是候选内容，不会直接改写正式知识库"/><div className="form-panel">
    <div className="notice compact-notice">日常换一批不需要AI。只有当本地知识库缺少某个主题，或你希望重写某个主题时，才在这里调用API；结果必须先到“内容审核”。</div>
    <label>学科<input value={subject} onChange={event=>setSubject(event.target.value)}/></label><label>想增加或重写的主题<input value={topic} onChange={event=>setTopic(event.target.value)} placeholder="例如：根升余弦滤波器"/></label>
    <label>服务商<select value={provider} onChange={event=>setProvider(event.target.value)}>{providers.data?.map(item=><option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label>
    <label>模型<select value={model} onChange={event=>setModel(event.target.value)}><option value="">请选择</option>{selected?.models?.map(item=><option key={item.id}>{item.id}</option>)}</select></label>
    <button disabled={!topic||!model} onClick={async()=>{try{const response=await post<any>('/ai/generate-card',{subject,topic,provider_id:provider,model,consent:true});setResult('候选内容已生成，请到“内容审核”确认，编号 '+response.review_id)}catch(error:any){setResult(error.message)}}}>生成通俗解释候选</button>{result&&<div className="notice">{result}</div>}
  </div></>;
}

export function NetworkUpdates(){const sources=useApi<any>('/sources'),[results,setResults]=useState<any[]>([]),[busy,setBusy]=useState(false);return <><PageTitle title="官方来源网络更新" actions={<button disabled={busy} onClick={async()=>{setBusy(true);try{setResults(await post<any[]>('/sources/check',{}))}finally{setBusy(false)}}}>{busy?'检查中…':'检查全部来源'}</button>}/><div className="notice">默认不调用付费 AI。HTTP 失败时会报告“检查失败/需要人工验证”，不会绕过验证码或访问控制。</div><div className="source-list">{sources.data?.sources?.map((s:any)=><article key={s.id}><div><Badge tone="green">{s.trust}</Badge><h3>{s.name}</h3><a href={s.url} target="_blank">{s.url}</a></div><span>每 {s.interval_hours} 小时</span></article>)}</div>{results.length>0&&<div className="panel"><h2>本次检查结果</h2>{results.map(x=><p key={x.id}><b>{x.name}</b>：{x.status}{x.error&&` — ${x.error}`}</p>)}</div>}</>}
export function ReviewQueue(){
  const r=useApi<any[]>('/reviews?status=pending');
  const label=(type:string)=>type==='knowledge_card'?'AI或导入的知识解释':type==='web_update'?'官方网页检测到变化':'待确认内容';
  return <><PageTitle title="内容审核" kicker="确认可靠后，候选内容才会进入正式知识库"/>
    <div className="review-guide"><h2>这里是做什么的？</h2><p>DeepSeek生成的新知识、批量导入内容，以及官方网站检测到的变化，都先暂存在这里。它们不会自动成为正式知识，避免AI错误或网页误判污染你的资料。</p><div><span><b>确认入库</b>：内容可信，可以正式使用</span><span><b>忽略</b>：不是有效更新或内容不需要</span></div></div>
    <div className="review-list">{r.data?.map(item=><article key={item.id}><div><Badge>{label(item.item_type)}</Badge><h2>{item.title}</h2><p>当前判断：{item.trust_level}</p>{item.source_url&&<a href={item.source_url} target="_blank" rel="noreferrer">打开原始网页 ↗</a>}<details><summary>查看候选内容</summary><pre>{(()=>{try{return JSON.stringify(JSON.parse(item.payload_json),null,2)}catch{return item.payload_json}})()}</pre></details></div><div><button onClick={async()=>{await post('/reviews/'+item.id+'/action',{action:'accept',trust_level:'已人工确认'});r.reload()}}>{item.item_type==='knowledge_card'?'确认入库':'标记已查看'}</button><button className="danger" onClick={async()=>{await post('/reviews/'+item.id+'/action',{action:'reject'});r.reload()}}>忽略</button></div></article>)}</div>
    {r.data?.length===0&&<div className="empty"><b>现在没有需要你确认的内容</b><p>这是正常状态。以后AI生成或官方网站出现真实变化时，才会在这里显示。</p></div>}
  </>;
}
export function MediaManager(){const r=useApi<any[]>('/media');return <><PageTitle title="图片与来源管理"/><div className="media-grid">{r.data?.map(x=><article key={x.id}><div className="media-icon">▧</div><b>{x.local_path.split(/[\\/]/).pop()}</b><span>{x.license}</span><p>{x.description||'尚无说明'}</p><details><summary>OCR 文字</summary><p>{x.ocr_text||'尚未识别'}</p></details></article>)}</div>{r.data?.length===0&&<div className="empty">尚无本地媒体，可从 OCR 页面上传。</div>}</>}

export function Statistics(){const d=useApi<any>('/dashboard'),s=useApi<any[]>('/subjects');const option={tooltip:{},xAxis:{type:'value',axisLabel:{color:'#526e64'},splitLine:{lineStyle:{color:'#d9e9dd'}}},yAxis:{type:'category',data:(s.data||[]).map(x=>x.name),axisLabel:{color:'#526e64'},axisLine:{lineStyle:{color:'#bcd4c4'}}},series:[{type:'bar',data:(s.data||[]).map(x=>x.count),itemStyle:{color:'#38ad83',borderRadius:4}}],grid:{left:150,right:30,top:20,bottom:40}};return <><PageTitle title="学习统计"/>{d.data&&<div className="stats"><Stat label="已接触" value={d.data.viewed}/><Stat label="已掌握" value={d.data.mastered}/><Stat label="待复习" value={d.data.reviews_due}/><Stat label="收藏" value={d.data.favorites}/></div>}<div className="panel">{s.data?<EChart option={option} height={640}/>:<Loading/>}</div></>}
export function Settings(){
  const r=useApi<Record<string,string>>('/settings'),[form,setForm]=useState<Record<string,string>>({});
  useEffect(()=>{if(r.data)setForm(r.data)},[r.data]);
  return <><PageTitle title="设置"/><div className="form-panel"><div className="setting-fixed"><span>网站背景</span><b>固定动态星空</b><p>背景只缓慢运动，不再按进入网站、日期或换一批自动更换图片。</p></div>
    <label>隐私确认<select value={form.privacy_confirmation||'always'} onChange={event=>setForm({...form,privacy_confirmation:event.target.value})}><option value="always">每次都确认</option><option value="images">仅图片确认</option><option value="threshold">费用超阈值确认</option></select></label>
    <label>局域网模式<select value={form.lan_enabled||'false'} onChange={event=>setForm({...form,lan_enabled:event.target.value})}><option value="false">关闭（下次启动生效）</option><option value="true">打开（需先设置密码）</option></select></label>
    <button onClick={async()=>{await put('/settings',{...form,background_mode:'dynamic_sky'});alert('设置已保存到 SQLite')}}>保存设置</button>
  </div></>;
}

export function AiConfig(){const r=useApi<Provider[]>('/ai/providers'),[edit,setEdit]=useState<any>(null),[msg,setMsg]=useState('');const blank=(id:string)=>({id:id.trim(),text_input:'untested',streaming:'untested',image_input:'untested',structured_output:'untested',reasoning:'untested',tool_calling:'untested',max_output_test:'untested',web_search:'untested'});return <><PageTitle title="API 服务配置" kicker="密钥仅写入 private/secrets.env"/><div className="provider-grid">{r.data?.map(p=><article key={p.id}><div><Badge tone={p.configured?'green':'amber'}>{p.configured?'已配置':'未配置'}</Badge><h2>{p.display_name}</h2><p>{p.base_url}</p><span>{p.models?.length||0} 个本地模型配置</span></div><button onClick={()=>setEdit({...p,api_key:''})}>配置</button></article>)}</div>{edit&&<div className="form-panel"><h2>配置 {edit.display_name}</h2><label>显示名称<input value={edit.display_name} onChange={e=>setEdit({...edit,display_name:e.target.value})}/></label><label>API 基础地址<input value={edit.base_url} onChange={e=>setEdit({...edit,base_url:e.target.value})}/></label><label>API Key（不会回显）<input type="password" value={edit.api_key} onChange={e=>setEdit({...edit,api_key:e.target.value})}/></label><label>手动模型 ID（逗号分隔）<input value={(edit.models||[]).map((x:any)=>x.id).join(',')} onChange={e=>setEdit({...edit,models:e.target.value.split(',').filter(Boolean).map(blank)})}/></label><div className="row"><button onClick={async()=>{await put(`/ai/providers/${edit.id}`,edit);setMsg('保存成功，密钥只在后端私密文件中');r.reload()}}>安全保存</button><button onClick={async()=>{try{const x=await post<any>(`/ai/providers/${edit.id}/models`,{});setEdit({...edit,models:x.models.map(blank)});setMsg(x.notice)}catch(e:any){setMsg(e.message)}}}>同步模型 ID</button></div>{msg&&<div className="notice">{msg}</div>}</div>}<div className="notice">能力状态必须通过短请求验证：文本、流式、结构化 JSON、图片、思考程度、工具调用、最大输出和原生联网搜索。同步模型列表不会自动宣称任何能力。</div></>}
export function Usage(){const r=useApi<any[]>('/ai/usage');return <><PageTitle title="AI 次数与费用统计"/><div className="compare"><table><thead><tr><th>时间</th><th>服务商 / 模型</th><th>功能</th><th>输入</th><th>输出</th><th>费用</th><th>状态</th></tr></thead><tbody>{r.data?.map(x=><tr key={x.id}><td>{new Date(x.created_at).toLocaleString()}</td><td>{x.provider}<br/>{x.model}</td><td>{x.feature}</td><td>{x.input_tokens??'未知'}</td><td>{x.output_tokens??'未知'}</td><td>{x.actual_cost??x.estimated_cost??'价格未知'}</td><td>{x.success?'成功':`失败 ${x.error_code||''}`}</td></tr>)}</tbody></table></div></>}
export function Backups(){const r=useApi<any[]>('/backups'),[msg,setMsg]=useState('');return <><PageTitle title="备份与恢复" actions={<button onClick={async()=>{const x=await post<any>('/backups',{});setMsg(`已创建：${x.path}`);r.reload()}}>创建手动备份</button>}/>{msg&&<div className="notice">{msg}</div>}<div className="source-list">{r.data?.map(x=><article key={x.path}><div><h3>{x.name}</h3><span>{(x.size/1024/1024).toFixed(2)} MB · {new Date(x.modified).toLocaleString()}</span></div><button onClick={async()=>{const v=await post<any>('/backups/verify',{path:x.path});alert(v.ok?'完整性校验通过':`损坏文件：${v.errors.join(',')}`)}}>验证完整性</button></article>)}</div><div className="notice">恢复操作会先验证备份，再自动备份当前状态；批处理请使用 restore.bat。</div></>}
export function Diagnostics(){const r=useApi<any>('/diagnostics');return <><PageTitle title="系统诊断" actions={<button onClick={r.reload}>重新检测</button>}/><div className="diag">{r.data?.checks.map((x:any)=><article key={x.name} className={x.ok?'pass':'fail'}><b>{x.ok?'✓':'!'}</b><div><h3>{x.name}</h3><p>{x.detail}</p></div></article>)}</div>{r.error&&<ErrorBox error={r.error}/>}</>}

export function SetupWizard(){const[step,setStep]=useState(0),[account,setAccount]=useState({username:'learner',password:''});const steps=['DeepSeek 配置','GPT 配置','本地 OCR','费用限制','局域网登录','连接测试','完成'];return <><PageTitle title="首次启动配置向导"/><div className="wizard"><div className="wizard-steps">{steps.map((x,i)=><span className={i<=step?'done':''} key={x}>{i+1}. {x}</span>)}</div><section><h2>{steps[step]}</h2>{step<2&&<p>可在“API 服务配置”安全填写密钥、同步模型并测试。现在可跳过，全部离线功能仍可使用。</p>}{step===2&&<p>诊断页会显示 PaddleOCR 状态；setup.bat 会安装 CPU 版并下载中文模型。</p>}{step===3&&<p>默认每日 50 次、每月 500 次；价格未知时不显示虚假精确费用。</p>}{step===4&&<><label>用户名<input value={account.username} onChange={e=>setAccount({...account,username:e.target.value})}/></label><label>密码（至少8位）<input type="password" value={account.password} onChange={e=>setAccount({...account,password:e.target.value})}/></label><button disabled={account.password.length<8} onClick={()=>post('/auth/setup',account).then(()=>alert('局域网账号已设置')).catch((e:any)=>alert(e.message))}>保存账号</button></>}{step===5&&<Link className="button" to="/diagnostics">打开系统诊断</Link>}{step===6&&<p>配置已完成。你可以随时在设置中修改，API Key 不会进入 SQLite、前端或日志。</p>}<div className="row"><button disabled={step===0} onClick={()=>setStep(s=>s-1)}>上一步</button>{step<6?<button onClick={()=>setStep(s=>s+1)}>下一步 / 跳过</button>:<button onClick={async()=>{await put('/settings',{setup_complete:'true'});location.href='/'}}>进入首页</button>}</div></section></div></>}
export function SearchPage(){const[p]=useSearchParams(),q=p.get('q')||'',r=useApi<any>(q?`/search?q=${encodeURIComponent(q)}`:null,[q]);return <><PageTitle title={`搜索：${q}`}/>{r.data&&<><h2>知识卡（{r.data.cards.length}）</h2><CardGrid cards={r.data.cards}/><h2>笔记（{r.data.notes.length}）</h2><div className="note-list">{r.data.notes.map((n:any)=><article key={n.id}><b>{n.title}</b><p>{n.content}</p></article>)}</div><h2>政策（{r.data.policies.length}）</h2>{r.data.policies.map((x:any)=><p key={x.id}>{x.institution} · {x.title}</p>)}</>}{q&&!r.data&&<Loading/>}</>}
