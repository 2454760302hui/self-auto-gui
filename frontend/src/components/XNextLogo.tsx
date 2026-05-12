import { Link } from '@tanstack/react-router';

export function XNextLogo({ size = 'default' }: { size?: 'default' | 'large' | 'small' }) {
  const dimensions = {
    small: { box: 'w-7 h-7', text: 'text-xs', label: 'text-sm' },
    default: { box: 'w-9 h-9', text: 'text-sm', label: 'text-base' },
    large: { box: 'w-12 h-12', text: 'text-lg', label: 'text-xl' },
  }[size];

  return (
    <Link to="/chat" className="flex items-center gap-2.5 group">
      {/* Outer breathing glow ring */}
      <div className="relative flex items-center justify-center">
        {/* Glow layers - three rings for depth */}
        <div
          className={`
            ${dimensions.box}
            absolute rounded-xl
            animate-logo-breathe-outer
            bg-gradient-to-br from-indigo-500 via-violet-600 to-cyan-500
          `}
        />
        <div
          className={`
            ${dimensions.box}
            absolute rounded-xl
            animate-logo-breathe-mid
            bg-gradient-to-br from-indigo-400 via-violet-500 to-cyan-400
          `}
        />
        {/* Core box with inner glow */}
        <div
          className={`
            ${dimensions.box} rounded-xl relative z-10
            bg-gradient-to-br from-indigo-600 via-violet-700 to-cyan-700
            flex items-center justify-center
            shadow-lg
            animate-logo-breathe-core
            transition-transform duration-200 group-hover:scale-105
          `}
        >
          {/* N letter */}
          <span
            className={`${dimensions.text} font-black text-white tracking-widest select-none`}
            style={{
              textShadow: '0 0 8px rgba(139, 92, 246, 0.8), 0 0 16px rgba(6, 182, 212, 0.5)',
              letterSpacing: '-0.02em',
            }}
          >
            N
          </span>
        </div>
      </div>
      {/* Brand text */}
      <span className={`${dimensions.label} font-bold tracking-tight`}>
        <span className="nextagent-gradient-text">Next</span>
        <span className="nextagent-text">Agent</span>
      </span>
    </Link>
  );
}
