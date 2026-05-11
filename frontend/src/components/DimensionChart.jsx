
import React from 'react';
import {
    Radar,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    ResponsiveContainer,
    Tooltip
} from 'recharts';

// Custom Tick Component for Multi-line Text
const CustomTick = ({ payload, x, y, textAnchor }) => {
    const words = payload.value.split(' ');
    return (
        <g className="recharts-layer recharts-polar-angle-axis-tick">
            <text
                x={x}
                y={y}
                textAnchor={textAnchor}
                fill="#4b5563"
                fontSize={9}
                fontWeight={600}
            >
                {words.map((word, i) => (
                    <tspan x={x} dy={i === 0 ? 0 : 9} key={i}>
                        {word}
                    </tspan>
                ))}
            </text>
        </g>
    );
};

/**
 * DimensionChart Component
 * Visualizes candidate dimensions using a Radar Chart.
 * 
 * @param {Object} props
 * @param {Object} props.dimensions - Object with dimension keys and scores (0-10)
 */
const DimensionChart = ({ dimensions, averageDimensions }) => {
    if (!dimensions) return null;

    const score = (value) => {
        const numeric = Number(value ?? 0);
        if (Number.isNaN(numeric)) return 0;
        return Math.max(0, Math.min(10, numeric));
    };

    // Format data for Recharts
    // Note: ensure spaces are present where line breaks are desired
    const data = [
        {
            subject: 'Project Done',
            A: score(dimensions.project_completion),
            B: score(averageDimensions?.project_completion),
            fullMark: 10,
        },
        {
            subject: 'Code Quality',
            A: score(dimensions.engineering_quality),
            B: score(averageDimensions?.engineering_quality),
            fullMark: 10,
        },
        {
            subject: 'Communication',
            A: score(dimensions.communication),
            B: score(averageDimensions?.communication),
            fullMark: 10,
        },
        {
            subject: 'Innovation',
            A: score(dimensions.innovation),
            B: score(averageDimensions?.innovation),
            fullMark: 10,
        },
        {
            subject: 'Depth',
            A: score(dimensions.depth_novelty),
            B: score(averageDimensions?.depth_novelty),
            fullMark: 10,
        },
    ];

    return (
        <div className="w-full h-[280px] sm:h-[320px] flex items-center justify-center overflow-visible">
            <ResponsiveContainer width="100%" height="100%">
                <RadarChart
                    cx="50%"
                    cy="50%"
                    outerRadius="62%"
                    data={data}
                    margin={{ top: 16, right: 18, left: 18, bottom: 16 }}
                >
                    <PolarGrid stroke="#e5e7eb" />
                    <PolarAngleAxis
                        dataKey="subject"
                        tick={<CustomTick />}
                    />
                    <PolarRadiusAxis
                        angle={30}
                        domain={[0, 10]}
                        tick={false}
                        axisLine={false}
                    />
                    <Tooltip
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        formatter={(value, name) => [Number(value).toFixed(1), name]}
                    />

                    {/* Average Score Radar (Background) */}
                    {averageDimensions && (
                        <Radar
                            name="Role Average"
                            dataKey="B"
                            stroke="#9ca3af"
                            fill="#9ca3af"
                            fillOpacity={0.1} // Lighter fill for background
                            strokeDasharray="4 4" // Dashed line for distinction
                        />
                    )}

                    {/* Candidate Score Radar (Foreground) */}
                    <Radar
                        name="Candidate Score"
                        dataKey="A"
                        stroke="#6366f1"
                        fill="#6366f1"
                        fillOpacity={0.6}
                    />

                </RadarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default DimensionChart;
