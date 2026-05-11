import React from 'react';

const DIMENSIONS = [
    {
        key: 'project_completion',
        label: 'Project Completion',
        short: 'Completion',
    },
    {
        key: 'engineering_quality',
        label: 'Code Quality',
        short: 'Quality',
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
        text: 'text-emerald-700',
        fill: 'from-emerald-500 to-teal-500',
        bg: 'bg-emerald-50',
        border: 'border-emerald-100',
    };
    if (value >= 4.5) return {
        text: 'text-amber-700',
        fill: 'from-amber-400 to-yellow-500',
        bg: 'bg-amber-50',
        border: 'border-amber-100',
    };
    return {
        text: 'text-red-700',
        fill: 'from-rose-500 to-red-500',
        bg: 'bg-red-50',
        border: 'border-red-100',
    };
};

const average = (items) => {
    if (!items.length) return 0;
    return items.reduce((sum, item) => sum + item.candidate, 0) / items.length;
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

    return (
        <div className="w-full space-y-4">
            <div className={`rounded-xl border ${tone.border} ${tone.bg} p-4`}>
                <div className="flex items-end justify-between gap-3">
                    <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Candidate</div>
                        <div className={`mt-1 text-3xl font-bold ${tone.text}`}>
                            {formatScore(candidateAverage)}
                            <span className="text-sm font-semibold text-gray-500">/10</span>
                        </div>
                    </div>
                    {roleAverage !== null && (
                        <div className="text-right">
                            <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Role Avg</div>
                            <div className="mt-1 text-lg font-bold text-gray-600">
                                {formatScore(roleAverage)}
                                <span className="text-xs font-semibold text-gray-400">/10</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="space-y-3">
                {rows.map((row) => {
                    const rowTone = getTone(row.candidate);
                    const candidatePercent = `${row.candidate * 10}%`;
                    const averagePercent = row.average === null ? null : `${row.average * 10}%`;

                    return (
                        <div key={row.key} className="space-y-1.5">
                            <div className="flex items-baseline justify-between gap-3">
                                <div className="min-w-0">
                                    <div className="text-sm font-semibold text-gray-800 truncate">{row.label}</div>
                                    <div className="text-[11px] font-medium text-gray-400">{row.short}</div>
                                </div>
                                <div className={`text-sm font-bold tabular-nums ${rowTone.text}`}>
                                    {formatScore(row.candidate)}
                                </div>
                            </div>

                            <div className="relative h-3 rounded-full bg-gray-100">
                                <div
                                    className={`absolute inset-y-0 left-0 rounded-full bg-gradient-to-r ${rowTone.fill}`}
                                    style={{ width: candidatePercent }}
                                />
                                {averagePercent && (
                                    <div
                                        className="absolute top-[-2px] h-7 w-0.5 rounded-full bg-gray-500/70"
                                        style={{ left: averagePercent }}
                                        title={`Role average ${formatScore(row.average)}/10`}
                                    />
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {averageDimensions && (
                <div className="flex items-center gap-4 text-[11px] font-semibold text-gray-500 pt-1">
                    <div className="flex items-center gap-1.5">
                        <span className="h-2.5 w-5 rounded-full bg-gradient-to-r from-rose-500 to-red-500" />
                        <span>Candidate</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <span className="h-4 w-0.5 rounded-full bg-gray-500/70" />
                        <span>Role Avg</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DimensionChart;
