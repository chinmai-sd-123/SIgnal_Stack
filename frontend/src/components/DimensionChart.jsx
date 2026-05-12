import React from 'react';

const DIMENSIONS = [
    {
        key: 'project_completion',
        label: 'Project Completion',
        short: 'Delivery',
    },
    {
        key: 'engineering_quality',
        label: 'Code Quality',
        short: 'Implementation',
    },
    {
        key: 'communication',
        label: 'Communication',
        short: 'Clarity',
    },
    {
        key: 'innovation',
        label: 'Innovation',
        short: 'Ideas',
    },
    {
        key: 'depth_novelty',
        label: 'Depth',
        short: 'Depth',
    },
];

const numberOrZero = (value) => {
    const numeric = Number(value ?? 0);
    return Number.isFinite(numeric) ? numeric : 0;
};

const detectScale = (dimensions, averageDimensions) => {
    const values = DIMENSIONS.flatMap(({ key }) => [
        numberOrZero(dimensions?.[key]),
        numberOrZero(averageDimensions?.[key]),
    ]);
    const max = Math.max(...values, 0);
    return max > 0 && max <= 1 ? 1 : 10;
};

const normalizeScore = (value, scale) => {
    const numeric = numberOrZero(value);
    const converted = scale === 1 ? numeric * 10 : numeric;
    return Math.max(0, Math.min(10, converted));
};

const formatScore = (value) => {
    if (value >= 9.95) return '10';
    if (value <= 0.05) return '0';
    return value.toFixed(1);
};

const getTone = (value) => {
    if (value >= 7) return {
        label: 'Strong',
        text: 'text-primary',
        fill: 'from-primary via-primary-hover to-accent',
        bg: 'from-primary/10 via-white to-accent/10',
        border: 'border-primary/20',
        chip: 'bg-primary-soft text-primary border-primary/20',
    };
    if (value >= 4.5) return {
        label: 'Developing',
        text: 'text-amber-700',
        fill: 'from-accent via-amber-400 to-primary-hover',
        bg: 'from-accent/14 via-white to-primary/8',
        border: 'border-accent/25',
        chip: 'bg-accent-soft text-amber-800 border-accent/25',
    };
    return {
        label: 'Needs Proof',
        text: 'text-rose-700',
        fill: 'from-rose-500 via-red-500 to-accent',
        bg: 'from-rose-50 via-white to-accent/10',
        border: 'border-rose-200',
        chip: 'bg-rose-50 text-rose-700 border-rose-200',
    };
};

const average = (items) => {
    if (!items.length) return 0;
    return items.reduce((sum, item) => sum + item.candidate, 0) / items.length;
};

const clampPercent = (value) => Math.max(0, Math.min(100, value * 10));

const formatDelta = (candidateAverage, roleAverage) => {
    if (roleAverage === null) return null;
    const delta = candidateAverage - roleAverage;
    if (Math.abs(delta) < 0.05) return 'Aligned with role avg';
    return `${delta > 0 ? '+' : ''}${delta.toFixed(1)} vs role avg`;
};

const DimensionChart = ({ dimensions, averageDimensions }) => {
    if (!dimensions) return null;

    const scale = detectScale(dimensions, averageDimensions);
    const rows = DIMENSIONS.map((dimension) => ({
        ...dimension,
        candidate: normalizeScore(dimensions?.[dimension.key], scale),
        average: averageDimensions
            ? normalizeScore(averageDimensions?.[dimension.key], scale)
            : null,
    }));

    const candidateAverage = average(rows);
    const roleAverage = averageDimensions ? average(rows.map((row) => ({ candidate: row.average ?? 0 }))) : null;
    const tone = getTone(candidateAverage);
    const deltaLabel = formatDelta(candidateAverage, roleAverage);

    return (
        <div className="w-full space-y-5">
            <div className={`rounded-2xl border ${tone.border} bg-gradient-to-br ${tone.bg} p-4 shadow-sm`}>
                <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                        <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-secondary">Candidate Avg</div>
                        <div className={`mt-1 flex items-end gap-1 font-bold ${tone.text}`}>
                            <span className="text-4xl leading-none tabular-nums">{formatScore(candidateAverage)}</span>
                            <span className="pb-1 text-sm font-semibold text-text-secondary">/10</span>
                        </div>
                        {deltaLabel && (
                            <div className="mt-2 text-xs font-semibold text-text-secondary">{deltaLabel}</div>
                        )}
                    </div>

                    {roleAverage !== null && (
                        <div className="shrink-0 rounded-xl border border-white/70 bg-white/70 px-3 py-2 text-right shadow-sm backdrop-blur">
                            <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-text-muted">Role Avg</div>
                            <div className="mt-1 text-lg font-bold tabular-nums text-text-main">
                                {formatScore(roleAverage)}
                                <span className="text-xs font-semibold text-text-muted">/10</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className={`mt-4 inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold ${tone.chip}`}>
                    {tone.label}
                </div>
            </div>

            <div className="space-y-4">
                {rows.map((row) => {
                    const rowTone = getTone(row.candidate);
                    const candidatePercent = clampPercent(row.candidate);
                    const averagePercent = row.average === null ? null : clampPercent(row.average);

                    return (
                        <div key={row.key} className="space-y-2">
                            <div className="flex items-baseline justify-between gap-3">
                                <div className="min-w-0">
                                    <div className="truncate text-sm font-bold text-text-main">{row.label}</div>
                                    <div className="text-[11px] font-semibold text-text-muted">{row.short}</div>
                                </div>
                                <div className={`shrink-0 text-sm font-bold tabular-nums ${rowTone.text}`}>
                                    {formatScore(row.candidate)}
                                </div>
                            </div>

                            <div
                                className="relative h-3 overflow-visible rounded-full border border-white bg-light-200 shadow-inner"
                                aria-label={`${row.label}: candidate ${formatScore(row.candidate)} out of 10${row.average !== null ? `, role average ${formatScore(row.average)} out of 10` : ''}`}
                            >
                                <div
                                    className={`absolute inset-y-0 left-0 rounded-full bg-gradient-to-r ${rowTone.fill} shadow-sm`}
                                    style={{
                                        width: `${candidatePercent}%`,
                                        minWidth: row.candidate > 0 ? '10px' : '0px',
                                    }}
                                />
                                {averagePercent !== null && (
                                    <div
                                        className="absolute -top-1 h-5 w-0.5 -translate-x-1/2 rounded-full bg-text-secondary shadow-[0_0_0_2px_rgba(255,253,248,0.92)]"
                                        style={{ left: `${Math.max(2, Math.min(98, averagePercent))}%` }}
                                        title={`Role average ${formatScore(row.average)}/10`}
                                    />
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {averageDimensions && (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-light-200 pt-3 text-[11px] font-semibold text-text-secondary">
                    <div className="flex items-center gap-1.5">
                        <span className="h-2.5 w-6 rounded-full bg-gradient-to-r from-primary via-primary-hover to-accent" />
                        <span>Candidate</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <span className="h-4 w-0.5 rounded-full bg-text-secondary" />
                        <span>Role Avg</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DimensionChart;
