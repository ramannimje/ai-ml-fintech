import { Hexagon, TrendingUp } from 'lucide-react';

export function Logo({ size = 28, className = '' }: { size?: number; className?: string }) {
    // A sleek combination of a Hexagon (structure/data) and TrendingUp (markets/intelligence)
    return (
        <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
            <Hexagon
                size={size}
                strokeWidth={1.5}
                style={{ color: 'var(--primary)' }}
                className="absolute inset-0 dark:text-[color-mix(in_srgb,var(--primary-soft)_40%,var(--text))] text-[var(--primary)]"
            />
            <TrendingUp
                size={size * 0.55}
                strokeWidth={2.5}
                style={{ color: 'var(--gold)' }}
                className="relative z-10"
            />
        </div>
    );
}
