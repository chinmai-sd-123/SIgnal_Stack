
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
                fontSize={10}
                fontWeight={600}
            >
                {words.map((word, i) => (
                    <tspan x={x} dy={i === 0 ? 0 : 10} key={i}>
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

    // Format data for Recharts
    // Note: ensure spaces are present where line breaks are desired
    const data = [
        {
            subject: 'Project Completion',
            A: dimensions.project_completion || 0,
            B: averageDimensions?.project_completion || 0,
            fullMark: 10,
        },
        {
            subject: 'Engineering Quality',
            A: dimensions.engineering_quality || 0,
            B: averageDimensions?.engineering_quality || 0,
            fullMark: 10,
        },
        {
            subject: 'Communication',
            A: dimensions.communication || 0,
            B: averageDimensions?.communication || 0,
            fullMark: 10,
        },
        {
            subject: 'Innovation', // Single word, no split needed
            A: dimensions.innovation || 0,
            B: averageDimensions?.innovation || 0,
            fullMark: 10,
        },
        {
            subject: 'Depth/ Novelty', // Added space to force split if needed, or keep as is
            A: dimensions.depth_novelty || 0,
            B: averageDimensions?.depth_novelty || 0,
            fullMark: 10,
        },
    ];

    return (
        <div className="w-full h-[350px] flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
                <RadarChart
                    cx="50%"
                    cy="50%"
                    outerRadius="70%"
                    data={data}
                    margin={{ top: 20, right: 30, left: 30, bottom: 20 }}
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
                        formatter={(value, name) => [value, name]}
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
