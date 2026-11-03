'use client';
import { useRef, useState } from 'react';
import { askNisha, NISHA, type ChatTurn, type FitContext } from '@/lib/nisha';
import { useSpeechInput } from '@/hooks/useSpeechInput';
import { useSpokenReplies } from '@/hooks/useSpokenReplies';
export default function NishaChat({context}:{context:FitContext}) {
  const [messages,setMessages]=useState<ChatTurn[]>([]);
  const [text,setText]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [source,setSource]=useState('');
  const [share,setShare]=useState(false); // consent to send measurements to Meta's model
  const lock=useRef(false);
  const voice=useSpokenReplies();
  async function send(value:string) {
    if(!value.trim()||lock.current)return;
    lock.current=true;setBusy(true);setError('');
    const next:ChatTurn[]=[...messages,{role:'user',content:value.trim()}];setMessages(next);setText('');
    try {
      const result=await askNisha(next,context,share);
      setMessages([...next,{role:'assistant',content:result.reply}]);setSource(result.source);
      if(voice.enabled)void voice.speak(result.reply,NISHA.voice,NISHA.id);
    }catch(cause){setError(cause instanceof Error?cause.message:'Could not reach Nisha.');}
    finally{lock.current=false;setBusy(false);}
  }
  const speech=useSpeechInput(value=>void send(value));
  return <section className="nisha-chat card" aria-label="Ask Nisha"><div className="nisha-chat-heading"><div><span className="eyebrow">YOUR FIT COMPANION</span><h2>Ask Nisha</h2></div><span className="fixture-tag">{source==='muse'?'Muse Spark':source==='engine-template'?'Engine template':'Voice + text'}</span></div><p className="field-note">{NISHA.greeting}</p><label className="field-note"><input type="checkbox" checked={share} onChange={event=>setShare(event.target.checked)}/> Share my measurements with Nisha’s AI (Meta Muse) for more detailed advice. Off: your fit is checked on our server and the AI sees only the verdicts. Common personal details are filtered before messages are sent.</label><div className="nisha-suggestions" aria-label="Suggested questions">{['Should I try a larger size?', 'Compare the nearby sizes.', 'What is uncertain here?'].map(question=><button key={question} disabled={busy} onClick={()=>setText(question)}>{question}<span aria-hidden="true">↗</span></button>)}</div><div className="chat-history" aria-live="polite">{messages.map((message,index)=><p key={index} className={`chat-turn ${message.role}`}><strong>{message.role==='user'?'You':'Nisha'}</strong>{message.content}{message.role==='assistant'&&<button className="text-button" onClick={()=>void voice.speak(message.content,NISHA.voice,NISHA.id)}>Hear reply</button>}</p>)}</div><form onSubmit={event=>{event.preventDefault();void send(text);}}><label className="sr-only" htmlFor="nisha-message">Message Nisha</label><input id="nisha-message" value={text} onChange={event=>setText(event.target.value)} placeholder="How does this size compare?" maxLength={2000}/><button className="primary-button" disabled={busy||!text.trim()}>{busy?'Thinking…':'Ask Nisha'}</button></form><div className="voice-controls"><button className="upload-button" disabled={!speech.supported||speech.processing||busy} onClick={()=>{voice.stop();voice.claimMicrophone();void speech.toggle();}}>{speech.listening?'Stop microphone':speech.processing?'Processing…':'Use microphone'}</button><label><input type="checkbox" checked={voice.enabled} onChange={event=>voice.toggleEnabled(event.target.checked)}/> Speak replies</label>{voice.speaking&&<button onClick={voice.stop}>Stop audio</button>}</div><p role="status" className="field-note">{speech.status||voice.status}</p>{(error||voice.error)&&<p role="alert" className="engine-error">{error||voice.error}</p>}</section>;
}
