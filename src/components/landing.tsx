import Image from 'next/image';
import Link from 'next/link';
import './landing.css';

// Small flat illustrations for the setting; the garment itself is always a styled view of a measured body.
const Hanger = () => <svg viewBox="0 0 120 70" fill="none" aria-hidden="true"><path d="M60 12a9 9 0 1 1 9 9c-5 0-9 3-9 8v3L6 62h108L60 32" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const Tape = () => <svg viewBox="0 0 120 44" fill="none" aria-hidden="true"><rect x="2" y="2" width="116" height="40" rx="8" fill="#f2e3b3" stroke="#5b6b50" strokeWidth="2.5"/>{Array.from({ length: 13 }, (_, i) => <path key={i} d={`M${10 + i * 8} 4v${i % 5 === 0 ? 16 : 9}`} stroke="#5b6b50" strokeWidth="2"/>)}</svg>;
const Tag = ({ size, tone }: { size: string; tone: string }) => <svg viewBox="0 0 110 54" aria-hidden="true" className={`land-tag ${tone}`}><path d="M2 27 26 2h80v50H26Z" /><circle cx="22" cy="27" r="5" fill="none" strokeWidth="2.5"/><text x="64" y="36" textAnchor="middle">{size}</text></svg>;
const Mannequin = () => <svg viewBox="0 0 60 110" aria-hidden="true"><circle cx="30" cy="12" r="10" fill="currentColor"/><path d="M8 28h44l-9 30 9 30H8l9-30Z" fill="currentColor"/><path d="M30 88v18M14 106h32" stroke="currentColor" strokeWidth="5"/></svg>;
const Bag = () => <svg viewBox="0 0 80 90" fill="none" aria-hidden="true"><rect x="4" y="26" width="72" height="60" rx="8" fill="#e9dcc4" stroke="#2c332b" strokeWidth="2.5"/><path d="M22 30V22a18 18 0 0 1 36 0v8" stroke="#2c332b" strokeWidth="3"/></svg>;
const Curtain = () => <svg viewBox="0 0 150 300" aria-hidden="true"><path d="M0 6h150" stroke="#2c332b" strokeWidth="5"/>{Array.from({ length: 6 }, (_, i) => <rect key={i} x={i * 25} y="10" width="23" height="290" fill={i % 2 ? '#b97a5c' : '#c98b6b'}/>)}</svg>;

export default function Landing() {
  return <div className="landing">
    <header className="land-header">
      <Link href="/" className="land-brand">stylewise</Link>
      <nav><Link href="/try" className="land-pill">Try on</Link><a href="#how">How it works</a><Link href="/try">Ask Nisha</Link></nav>
    </header>
    <main>
      <section className="land-hero">
        <div>
          <p className="land-eyebrow">FIND YOUR SIZE BEFORE YOU BUY</p>
          <h1>See how every size<br/><em>sits on your shape.</em></h1>
          <p className="land-lede">Real brand size charts, a body built from your shape and size, and an honest answer for every size. No model faces.</p>
          <div className="land-actions"><Link href="/try" className="land-primary">Start fitting</Link><a href="#how" className="land-secondary">See how it works</a></div>
        </div>
        <div className="land-room">
          <div className="land-curtain"><Curtain/></div>
          <figure className="land-figure"><Image src="/landing/hero.jpg" alt="A black midi dress, size M, on a faceless mannequin with a size-M body" width={420} height={560} priority/>
            <figcaption><small>Size M</small><strong>Close at the waist, room at the hips</strong></figcaption></figure>
          <div className="land-hanger"><Hanger/></div><div className="land-bag"><Bag/></div>
          <div className="land-room-tag"><Tag size="M" tone="ok"/></div><div className="land-tape"><Tape/></div>
        </div>
      </section>

      <section className="land-usp" aria-label="What makes Stylewise different">
        <article><Tape/><div><h2>Measured, not guessed</h2><p>Brand charts in centimetres against a body built from your shape and size.</p></div></article>
        <article><Tag size="L" tone="olive"/><div><h2>Every size has a verdict</h2><p>Snug, fits or roomy, region by region, and the best fit for you.</p></div></article>
        <article><span className="land-mannequin"><Mannequin/></span><div><h2>Your shape, no model faces</h2><p>Every shape from XS to 3XL, women and men, on a calm faceless mannequin.</p></div></article>
      </section>

      <section className="land-how" id="how">
        <h2>How it works</h2>
        <div className="land-steps">
          <article><div className="land-step-art shapes">{['hourglass', 'triangle', 'rectangle', 'inverted', 'oval'].map(shape => <span key={shape} className={shape === 'rectangle' ? 'on' : ''}><Mannequin/></span>)}</div><h3><b>1</b>Pick your shape</h3><p>Five silhouettes, your usual size and height, or your own measurements.</p></article>
          <article><div className="land-step-art garments"><Hanger/><div>{['zesica-black-midi-dress', 'emerald-wrap-dress', 'parthvi-anarkali-set'].map(id => <Image key={id} src={`/api/assets/garment_photos/${id}.jpg`} alt="" width={84} height={84} unoptimized/>)}</div></div><h3><b>2</b>Pick a garment</h3><p>Dresses, tops, sets and menswear, each with its own size chart.</p></article>
          <article><div className="land-step-art sizes"><figure><Image src="/landing/body-s.jpg" alt="Dress size M on a size-S body: roomy" width={110} height={150}/><Tag size="S" tone="olive"/></figure><figure><Image src="/landing/body-m.jpg" alt="Dress size M on a size-M body: fits" width={110} height={150}/><Tag size="M" tone="ok"/></figure><figure><Image src="/landing/body-l.jpg" alt="Dress size M on a size-L body: tight" width={110} height={150}/><Tag size="L" tone="warn"/></figure></div><h3><b>3</b>See how it sits</h3><p>The same dress on different bodies, front, side and back, with a verdict for every size and a sizing assistant, Nisha.</p></article>
        </div>
      </section>

      <section className="land-cta"><h2>Ready to check a size?</h2><Link href="/try" className="land-primary">Open the fitting room</Link></section>
    </main>
    <footer className="land-footer"><span>stylewise</span><p>A visual guide and a size-chart comparison, built with Meta MHR, Muse Spark Open, Muse Image and SAM 3.1.</p></footer>
  </div>;
}
