import React, { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  Leaf,
  Sparkles,
  Heart,
  Smile,
  HeartHandshake,
  MessageCircle,
  PhoneCall,
  BookOpen,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";

// ─── Scroll Reveal Wrapper ─────────────────────────────────────────────────
interface RevealProps {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}

const Reveal: React.FC<RevealProps> = ({
  children,
  delay = 0,
  className = "",
}) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReduced) return;

    el.style.opacity = "0";
    el.style.transform = "translateY(40px)";
    el.style.transition = `opacity 0.8s cubic-bezier(0.16,1,0.3,1) ${delay}ms, transform 0.8s cubic-bezier(0.16,1,0.3,1) ${delay}ms`;

    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.style.opacity = "1";
          el.style.transform = "translateY(0)";
          obs.unobserve(el);
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.1 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [delay]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
};

// ─── Navbar ────────────────────────────────────────────────────────────────
const Navbar: React.FC = () => (
  <nav className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-6 py-4 bg-white/90 backdrop-blur-md border-b-2 border-gray-100">
    <div className="flex items-center gap-2">
      <div className="w-10 h-10 bg-[#ff9b71] rounded-full flex items-center justify-center text-white -rotate-12 hover:rotate-0 transition-transform duration-300">
        <Leaf size={20} strokeWidth={2.5} />
      </div>
      <span className="text-2xl font-extrabold text-[#191c1e] tracking-tight">
        MindMitra
      </span>
    </div>

    <div className="hidden md:flex items-center gap-8">
      {["Features", "How it Works", "About"].map((label) => (
        <a
          key={label}
          href={`#${label.toLowerCase().replace(/\s+/g, "-")}`}
          className="text-sm font-semibold text-[#414751] hover:text-[#ff9b71] transition-colors"
        >
          {label}
        </a>
      ))}
    </div>

    <Link
      to="/home"
      className="bg-[#ff9b71] hover:bg-[#ff8554] text-white font-semibold text-sm py-3 px-8 rounded-full transition-all duration-300 shadow-[0_4px_14px_0_rgba(255,155,113,0.39)] hover:shadow-[0_6px_20px_rgba(255,155,113,0.23)] hover:-translate-y-1 hover:scale-105"
    >
      Sign Up
    </Link>
  </nav>
);

// ─── Hero Section ──────────────────────────────────────────────────────────
const HeroSection: React.FC = () => {
  return (
    <section className="mt-30 hero-bg relative py-20 px-6 overflow-hidden flex flex-col md:flex-row items-center justify-center max-w-[1200px] mx-auto gap-12 rounded-4xl my-8 border-2 border-gray-100">
      {/* Blobs */}
      <div className="absolute top-10 left-10 w-72 h-72 bg-[#ffd166] rounded-full mix-blend-multiply filter blur-3xl opacity-50 blob-shape" />
      <div
        className="absolute bottom-10 right-10 w-80 h-80 bg-[#c3b1e1] rounded-full mix-blend-multiply filter blur-3xl opacity-40 blob-shape"
        style={{ animationDelay: "2s" }}
      />
      <div
        className="absolute top-1/2 left-1/2 w-64 h-64 bg-[#b9f382] rounded-full mix-blend-multiply filter blur-3xl opacity-40 blob-shape"
        style={{ animationDelay: "4s" }}
      />

      {/* Left: Text */}
      <div className="relative z-10 flex-1 flex flex-col items-start text-left pl-4 md:pl-12">
        <div className="stagger-1 inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border-2 border-gray-100 mb-6 shadow-sm hover:shadow-md transition-shadow">
          <Sparkles size={14} className="text-[#ff9b71] animate-pulse" />
          <span className="text-xs font-bold uppercase tracking-wider text-[#191c1e]">
            Your safe space
          </span>
        </div>

        <h1 className="stagger-2 text-[48px] leading-[1.1] font-extrabold text-[#191c1e] mb-6 max-w-xl tracking-tight">
          Your Caring Companion for <br />
          <span className="text-[#00457f] relative inline-block">
            Mental Wellness
            <svg
              className="absolute w-full h-4 -bottom-1 left-0 text-[#ffd166]"
              viewBox="0 0 100 20"
              preserveAspectRatio="none"
            >
              <path
                d="M0,10 Q50,20 100,10"
                fill="none"
                stroke="currentColor"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray="100"
                strokeDashoffset="100"
                style={{ animation: "dash 2s ease-out forwards" }}
              />
            </svg>
          </span>
        </h1>

        <p className="stagger-3 text-lg font-medium text-[#414751] mb-10 max-w-lg leading-relaxed">
          A safe space that listens and understands how you feel. Real-time
          support and gentle guidance whenever you need a friend.
        </p>

        <div className="stagger-4 flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          <Link
            to="/home"
            className="magnetic-button bg-[#00457f] hover:bg-[#003666] text-white font-bold text-lg py-4 px-8 rounded-full shadow-[0_8px_20px_rgba(0,69,127,0.2)] transition-all duration-300 w-full sm:w-auto text-center"
            onMouseMove={(e) => {
              const el = e.currentTarget as HTMLAnchorElement;
              const rect = el.getBoundingClientRect();
              const x = e.clientX - rect.left - rect.width / 2;
              const y = e.clientY - rect.top - rect.height / 2;
              el.style.transform = `translate(${x * 0.15}px, ${y * 0.15}px) scale(1.02)`;
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.transform =
                "translate(0px, 0px) scale(1)";
            }}
          >
            Start Feeling Better
          </Link>
          <a
            href="#features"
            className="bg-white border-2 border-gray-200 text-[#191c1e] font-bold text-lg py-4 px-8 rounded-full hover:border-[#00457f] hover:text-[#00457f] transition-all duration-300 w-full sm:w-auto text-center hover:shadow-lg hover:-translate-y-1"
          >
            Learn More
          </a>
        </div>
      </div>

      {/* Right: Illustration */}
      <div className="flex-1 w-full relative z-10 flex justify-center p-8 stagger-2">
        <div className="w-full max-w-md aspect-square bg-[#b9f382] rounded-full flex flex-col items-center justify-center shadow-[0_20px_50px_rgba(185,243,130,0.3)] relative overflow-visible border-4 border-white">
          <div className="absolute -top-6 -right-6 w-20 h-20 bg-[#ff9b71] rounded-full flex items-center justify-center rotate-12 shadow-lg border-4 border-white hover:scale-110 hover:rotate-[24deg] transition-all duration-300">
            <Heart size={28} className="text-white" fill="white" />
          </div>
          <div className="absolute -bottom-4 -left-4 w-16 h-16 bg-[#c3b1e1] rounded-full flex items-center justify-center -rotate-12 shadow-lg border-4 border-white hover:scale-110 hover:-rotate-[24deg] transition-all duration-300">
            <Smile size={24} className="text-white" />
          </div>
          <span className="text-8xl mb-4 hover:scale-110 transition-transform duration-300 cursor-default select-none">
            🌻
          </span>
          <h3 className="text-[#284d00] font-bold text-center px-8 text-xl">
            We're here for you,
            <br />
            every step.
          </h3>
        </div>
      </div>

    </section>
  );
};

// ─── Features Section ──────────────────────────────────────────────────────
const FeaturesSection: React.FC = () => (
  <section
    id="features"
    className="py-24 px-6 max-w-[1200px] mx-auto reveal-on-scroll"
  >
    <div className="text-center mb-16">
      <h2 className="text-[36px] font-bold text-[#191c1e] mb-4 tracking-tight">
        A Space That Understands You
      </h2>
      <p className="text-lg font-medium text-[#414751] max-w-2xl mx-auto">
        Gentle tools crafted to help you navigate your emotional landscape with
        warmth and care.
      </p>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      {/* Card 1 — Wide: Gentle Check-ins */}
      <Reveal
        delay={100}
        className="glass-panel p-10 rounded-[2.5rem] flex flex-col justify-between col-span-1 md:col-span-2 lg:col-span-2 bg-[#f0f7ff] border-none"
      >
        <div className="relative z-10">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mb-6 shadow-sm text-[#00457f]">
            <HeartHandshake size={30} />
          </div>
          <h3 className="text-2xl font-semibold text-[#191c1e] mb-3">
            Gentle Check-ins
          </h3>
          <p className="text-base font-medium text-[#414751] max-w-md">
            We pay attention to your words and feelings to understand how you're
            really doing, processing everything safely on your own device.
          </p>
        </div>
        <div className="mt-10 relative h-56 w-full rounded-[2rem] bg-[#ffd166] flex items-center justify-center border-4 border-white shadow-inner overflow-hidden z-10">
          <div
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage:
                "radial-gradient(circle at 2px 2px, black 1px, transparent 0)",
              backgroundSize: "20px 20px",
            }}
          />
          <span className="text-6xl relative z-10 hover:scale-125 transition-transform duration-300 cursor-default">
            🌟✨
          </span>
        </div>
      </Reveal>

      {/* Card 2 — Supportive Chat */}
      <Reveal
        delay={200}
        className="glass-panel p-10 rounded-[2.5rem] flex flex-col col-span-1 bg-[#fff5f0] border-none"
      >
        <div className="relative z-10">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mb-6 shadow-sm text-[#ff9b71]">
            <MessageCircle size={30} />
          </div>
          <h3 className="text-2xl font-semibold text-[#191c1e] mb-3">
            Supportive Chat
          </h3>
          <p className="text-base font-medium text-[#414751] flex-grow">
            Warm, guided conversations to help you navigate difficult feelings,
            available whenever you need someone to talk to.
          </p>
        </div>
        <div className="mt-8 space-y-4 z-10 relative">
          <div className="bg-white rounded-[1.5rem] rounded-tl-sm p-4 text-base font-medium text-[#191c1e] w-[85%] shadow-sm border border-gray-100 hover:-translate-y-1 transition-transform">
            I'm here for you. How are you feeling today?
          </div>
          <div className="bg-[#ff9b71] text-white rounded-[1.5rem] rounded-tr-sm p-4 text-base font-medium w-[85%] ml-auto text-right shadow-sm hover:-translate-y-1 transition-transform">
            I've been feeling a bit overwhelmed lately.
          </div>
        </div>
      </Reveal>

      {/* Card 3 — Immediate Help */}
      <Reveal
        delay={300}
        className="glass-panel p-10 rounded-[2.5rem] flex flex-col col-span-1 bg-[#f4f0ff] border-none"
      >
        <div className="relative z-10">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mb-6 shadow-sm text-[#c3b1e1]">
            <PhoneCall size={30} />
          </div>
          <h3 className="text-2xl font-semibold text-[#191c1e] mb-3">
            Immediate Help
          </h3>
          <p className="text-base font-medium text-[#414751] mb-8">
            When things feel too heavy, we'll gently connect you with the right
            crisis support and friendly resources right away.
          </p>
        </div>
        <div className="mt-auto h-32 w-full rounded-[2rem] bg-[#c3b1e1] flex items-center justify-center border-4 border-white z-10 relative group">
          <span className="text-5xl group-hover:scale-110 transition-transform duration-300 cursor-default">
            🫂
          </span>
        </div>
      </Reveal>

      {/* Card 4 — Personal Journal (wide) */}
      <Reveal
        delay={400}
        className="glass-panel p-10 rounded-[2.5rem] flex flex-col col-span-1 md:col-span-2 lg:col-span-2 bg-[#f0fdf4] border-none"
      >
        <div className="relative z-10 w-16 h-16 bg-white rounded-full flex items-center justify-center mb-6 shadow-sm text-[#4ade80]">
          <BookOpen size={30} />
        </div>
        <div className="flex flex-col md:flex-row gap-10 items-center relative z-10">
          <div className="flex-1">
            <h3 className="text-2xl font-semibold text-[#191c1e] mb-3">
              Your Personal Journal
            </h3>
            <p className="text-base font-medium text-[#414751]">
              Reflect on your days and see your growth. We'll help you spot what
              makes you feel best and celebrate your little victories.
            </p>
          </div>
          <div className="flex-1 w-full flex flex-wrap gap-3 justify-center md:justify-end">
            {[
              { label: "Calm 🌊", cls: "text-[#00457f] border-[#d3e3ff]" },
              { label: "Focused 🎯", cls: "text-[#ff9b71] border-[#ffeedd]" },
              { label: "Tired 🥱", cls: "text-[#414751] border-gray-200" },
              {
                label: "Grateful ✨",
                cls: "text-[#284d00] bg-[#b9f382] border-white scale-110 rotate-2 hover:rotate-6",
              },
            ].map(({ label, cls }) => (
              <span
                key={label}
                className={`px-6 py-3 bg-white font-bold text-sm rounded-full shadow-sm border-2 hover:scale-105 transition-all cursor-default ${cls}`}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </Reveal>
    </div>
  </section>
);

// ─── How It Works Section ──────────────────────────────────────────────────
const HowItWorksSection: React.FC = () => (
  <section
    id="how-it-works"
    className="py-24 px-6 bg-white relative overflow-hidden reveal-on-scroll"
  >
    <div
      className="absolute top-0 left-0 w-full h-full opacity-40"
      style={{
        backgroundImage: "radial-gradient(#f2f4f6 2px, transparent 2px)",
        backgroundSize: "32px 32px",
      }}
    />
    <div className="max-w-[1200px] mx-auto relative z-10">
      <div className="text-center mb-20">
        <h2 className="text-[36px] font-bold text-[#191c1e] mb-4 tracking-tight">
          A Simple Path to Clarity
        </h2>
        <p className="text-lg font-medium text-[#414751] max-w-2xl mx-auto">
          Three seamless steps to begin your journey toward feeling more like
          yourself.
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-12 relative">
        {/* Connecting gradient line */}
        <div className="hidden md:block absolute top-12 left-[15%] right-[15%] h-2 bg-gradient-to-r from-[#ffd166] via-[#ff9b71] to-[#c3b1e1] rounded-full z-0 opacity-30" />

        {[
          {
            num: "1",
            bg: "bg-[#ffd166]",
            textColor: "text-[#191c1e]",
            shape: "rounded-[2rem] -rotate-6 hover:rotate-0",
            title: "Create Your Safe Space",
            desc: "Set up a private, secure profile that acts as your personal sanctuary, entirely yours alone.",
            delay: 100,
          },
          {
            num: "2",
            bg: "bg-[#ff9b71]",
            textColor: "text-white",
            shape: "rounded-full scale-110 hover:scale-125",
            title: "Express Yourself Safely",
            desc: "Share your feelings naturally. Everything stays right on your device, never sent away to the cloud.",
            delay: 200,
          },
          {
            num: "3",
            bg: "bg-[#c3b1e1]",
            textColor: "text-white",
            shape: "rounded-[2rem] rotate-6 hover:rotate-0",
            title: "Receive Warm Support",
            desc: "Get gentle exercises and friendly coping strategies crafted just for what you're going through right now.",
            delay: 300,
          },
        ].map(({ num, bg, textColor, shape, title, desc, delay }) => (
          <Reveal
            key={num}
            delay={delay}
            className="flex-1 relative z-10 flex flex-col items-center text-center"
          >
            <div
              className={`w-24 h-24 ${bg} flex items-center justify-center mb-8 shadow-lg ${textColor} text-4xl font-extrabold border-4 border-white transition-all duration-300 hover:scale-110 ${shape}`}
            >
              {num}
            </div>
            <h3 className="text-2xl font-semibold text-[#191c1e] mb-3">
              {title}
            </h3>
            <p className="text-base font-medium text-[#414751]">{desc}</p>
          </Reveal>
        ))}
      </div>
    </div>
  </section>
);

// ─── Privacy & Trust Section ───────────────────────────────────────────────
const PrivacySection: React.FC = () => (
  <section
    id="about"
    className="py-24 px-6 max-w-[1200px] mx-auto text-center reveal-on-scroll"
  >
    <div className="max-w-4xl mx-auto bg-[#b9f382] p-12 md:p-16 rounded-[3rem] shadow-[0_20px_50px_rgba(185,243,130,0.2)] border-4 border-white relative overflow-hidden group hover:shadow-[0_25px_60px_rgba(185,243,130,0.3)] transition-shadow duration-500">
      <div className="absolute -top-10 -left-10 w-40 h-40 bg-white rounded-full opacity-20 group-hover:scale-110 transition-transform duration-700" />
      <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-white rounded-full opacity-20 group-hover:scale-110 transition-transform duration-700" />

      <div className="w-24 h-24 bg-white rounded-full mx-auto flex items-center justify-center shadow-sm mb-6 group-hover:rotate-[360deg] transition-transform duration-1000 ease-in-out">
        <ShieldCheck size={48} className="text-[#284d00]" />
      </div>

      <h2 className="text-[36px] font-black text-[#284d00] mb-6 tracking-tight">
        Your Privacy is Our Priority
      </h2>
      <p className="text-xl font-medium text-[#376700]/80 mb-10 max-w-2xl mx-auto">
        We believe your personal journey should be completely private. We use
        top-tier security measures so that your thoughts and feelings stay
        entirely with you. We never see your personal data.
      </p>

      <div className="flex flex-wrap justify-center gap-4">
        {[
          "End-to-End Security",
          "Stored Only on Your Device",
          "Completely Confidential",
        ].map((label) => (
          <div
            key={label}
            className="flex items-center gap-3 bg-white rounded-full px-6 py-4 shadow-sm hover:scale-105 hover:shadow-md transition-all cursor-default"
          >
            <CheckCircle2 size={20} className="text-[#ff9b71]" />
            <span className="text-sm font-bold text-[#191c1e]">{label}</span>
          </div>
        ))}
      </div>
    </div>
  </section>
);

// ─── Footer ─────────────────────────────────────────────────────────────────
const Footer: React.FC = () => (
  <footer className="bg-white w-full py-12 px-6 flex flex-col md:flex-row justify-between items-center gap-8 border-t-2 border-gray-100 mt-8">
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 bg-[#ff9b71] rounded-full flex items-center justify-center text-white">
        <Leaf size={16} strokeWidth={2.5} />
      </div>
      <span className="text-2xl font-extrabold text-[#191c1e]">MindMitra</span>
    </div>

    <nav className="flex flex-col md:flex-row items-center gap-8">
      {[
        { label: "Privacy Policy", href: "#" },
        { label: "Terms of Service", href: "#" },
        {
          label: "support@mindmitra.app",
          href: "mailto:support@mindmitra.app",
        },
      ].map(({ label, href }) => (
        <a
          key={label}
          href={href}
          className="text-sm font-bold text-[#414751] hover:text-[#ff9b71] transition-all duration-300"
        >
          {label}
        </a>
      ))}
    </nav>

    <p className="text-base font-medium text-[#414751]">
      © 2026 MindMitra. All rights reserved.
    </p>
  </footer>
);

// ─── Landing Page Root ─────────────────────────────────────────────────────
const LandingPage: React.FC = () => {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      document.querySelectorAll(".reveal-on-scroll").forEach((el) => {
        (el as HTMLElement).style.opacity = "1";
        (el as HTMLElement).style.transform = "none";
      });
      return;
    }

    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            obs.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.1 },
    );

    document
      .querySelectorAll(".reveal-on-scroll")
      .forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <div className="min-h-screen font-sans antialiased overflow-x-clip">
      <Navbar />
      <main className="flex-grow pb-16">
        <HeroSection />
        <FeaturesSection />
        <HowItWorksSection />
        <PrivacySection />
      </main>
      <Footer />
    </div>
  );
};

export default LandingPage;
