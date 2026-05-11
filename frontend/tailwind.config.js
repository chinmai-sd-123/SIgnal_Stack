/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Sora', 'Manrope', 'system-ui', 'sans-serif'],
            },
            colors: {
                // Primary Premium Palette
                primary: {
                    DEFAULT: '#0b5f66',
                    hover: '#0f766e',
                    soft: '#e6f6f5',
                    glow: 'rgba(11, 95, 102, 0.32)',
                },
                accent: {
                    DEFAULT: '#c9a227',
                    soft: '#f7efd2',
                },
                // Dark Theme Backgrounds
                dark: {
                    900: '#0C0C0E',
                    800: '#141416',
                    700: '#1C1C1F',
                    600: '#242428',
                },
                // Light Backgrounds
                light: {
                    50: '#f7f5f0',
                    100: '#f2eee6',
                    200: '#e6e1d7',
                },
                // Text
                text: {
                    primary: '#0f172a',
                    secondary: '#475569',
                    muted: '#94a3b8',
                },
                // Status
                success: '#22C55E',
                warning: '#F59E0B',
                error: '#EF4444',
            },
            borderRadius: {
                '2xl': '16px',
                '3xl': '24px',
            },
            boxShadow: {
                'glow': '0 0 30px rgba(11, 95, 102, 0.22)',
                'glow-sm': '0 0 15px rgba(11, 95, 102, 0.16)',
                'card': '0 10px 30px rgba(15, 23, 42, 0.08)',
                'hover': '0 18px 44px rgba(15, 23, 42, 0.16)',
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out',
                'slide-up': 'slideUp 0.4s ease-out',
                'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
                'float': 'float 3s ease-in-out infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                pulseGlow: {
                    '0%, 100%': { boxShadow: '0 0 20px rgba(67, 56, 202, 0.25)' },
                    '50%': { boxShadow: '0 0 40px rgba(99, 102, 241, 0.35)' },
                },
                float: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-5px)' },
                },
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
                'hero-gradient': 'linear-gradient(135deg, #0b5f66 0%, #0f766e 50%, #c9a227 110%)',
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
        require('@tailwindcss/forms'),
    ],
}
