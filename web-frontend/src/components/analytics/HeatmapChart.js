// HeatmapChart - built with recharts (no extra deps needed)
import {
  Cell,
  Rectangle,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ScatterChart,
  Scatter,
} from "recharts";

const HEAT_COLORS = [
  "#0d2a4d",
  "#0a4080",
  "#0060bf",
  "#0080ff",
  "#33a3ff",
  "#66c2ff",
];

const getColor = (value, min, max) => {
  if (max === min) return HEAT_COLORS[0];
  const ratio = (value - min) / (max - min);
  const idx = Math.min(
    Math.floor(ratio * HEAT_COLORS.length),
    HEAT_COLORS.length - 1,
  );
  return HEAT_COLORS[idx];
};

const transformDataForHeatmap = (data, xKey, yKey, valueKey) => {
  if (!data || data.length === 0)
    return { points: [], xLabels: [], yLabels: [], min: 0, max: 0 };
  const xLabels = Array.from(new Set(data.map((d) => d[xKey])));
  const yLabels = Array.from(new Set(data.map((d) => d[yKey])));
  const values = data.map((d) => d[valueKey]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const points = data.map((d) => ({
    x: xLabels.indexOf(d[xKey]),
    y: yLabels.indexOf(d[yKey]),
    value: d[valueKey],
    xLabel: d[xKey],
    yLabel: d[yKey],
  }));
  return { points, xLabels, yLabels, min, max };
};

const HeatmapChart = ({
  data = [],
  xKey = "x",
  yKey = "y",
  valueKey = "value",
  height = 300,
}) => {
  const { points, xLabels, yLabels, min, max } = transformDataForHeatmap(
    data,
    xKey,
    yKey,
    valueKey,
  );

  if (points.length === 0) {
    return (
      <p style={{ color: "#888", textAlign: "center" }}>
        No heatmap data available
      </p>
    );
  }

  const scatterData = points.map((p) => ({
    ...p,
    fill: getColor(p.value, min, max),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 60 }}>
        <XAxis
          dataKey="x"
          type="number"
          tickFormatter={(v) => xLabels[v] || v}
          stroke="#666"
          domain={[-0.5, xLabels.length - 0.5]}
        />
        <YAxis
          dataKey="y"
          type="number"
          tickFormatter={(v) => yLabels[v] || v}
          stroke="#666"
          domain={[-0.5, yLabels.length - 0.5]}
        />
        <Tooltip
          cursor={false}
          contentStyle={{
            backgroundColor: "rgba(15,20,30,0.95)",
            border: "1px solid #333",
            borderRadius: "8px",
            color: "white",
          }}
          formatter={(_, __, props) => [
            props.payload.value,
            `${props.payload.xLabel} / ${props.payload.yLabel}`,
          ]}
        />
        <Scatter
          data={scatterData}
          shape={(props) => {
            const { cx, cy, payload } = props;
            return (
              <Rectangle
                x={cx - 18}
                y={cy - 18}
                width={36}
                height={36}
                fill={payload.fill}
                radius={4}
              />
            );
          }}
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
};

export default HeatmapChart;
export { transformDataForHeatmap };
