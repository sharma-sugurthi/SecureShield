'use client';

/**
 * Coverage Ring — Animated circular progress indicator
 * Used to show coverage percentage in a visually appealing donut chart.
 */

export default function CoverageRing({ percentage = 0, size = 140, strokeWidth = 8 }) {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;

    let color = '#22C55E'; // green
    if (percentage < 50) color = '#EF4444'; // red
    else if (percentage < 80) color = '#F59E0B'; // amber

    return (
        <div className="coverage-ring" style={{ width: size, height: size }}>
            <svg viewBox={`0 0 ${size} ${size}`}>
                <circle className="bg" cx={size / 2} cy={size / 2} r={radius} />
                <circle
                    className="progress"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={color}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                />
            </svg>
            <span className="coverage-value" style={{ color }}>{percentage}%</span>
            <span className="coverage-label">Coverage</span>
        </div>
    );
}
