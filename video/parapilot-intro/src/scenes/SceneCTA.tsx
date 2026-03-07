import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  spring,
  useVideoConfig,
} from "remotion";
import { colors, fonts, fullScreen } from "../styles";

export const SceneCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const cmdScale = spring({
    frame: frame - 10,
    fps,
    from: 0.8,
    to: 1,
    durationInFrames: 25,
  });

  const githubOpacity = interpolate(frame, [60, 80], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const licenseOpacity = interpolate(frame, [100, 120], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Pulsing glow on the install command
  const glowIntensity = interpolate(
    Math.sin(frame * 0.08),
    [-1, 1],
    [0.3, 0.8]
  );

  return (
    <AbsoluteFill style={fullScreen}>
      {/* Install command */}
      <div
        style={{
          opacity: fadeIn,
          transform: `scale(${cmdScale})`,
          marginBottom: 60,
        }}
      >
        <div
          style={{
            backgroundColor: "#0d1117",
            borderRadius: 16,
            padding: "28px 48px",
            fontFamily: fonts.mono,
            fontSize: 36,
            border: `2px solid ${colors.accent}`,
            boxShadow: `0 0 ${40 * glowIntensity}px ${colors.accent}40`,
          }}
        >
          <span style={{ color: colors.green }}>$ </span>
          <span style={{ color: colors.white }}>
            pip install mcp-server-viznoir
          </span>
        </div>
      </div>

      {/* GitHub link */}
      <div
        style={{
          opacity: githubOpacity,
          display: "flex",
          alignItems: "center",
          gap: 16,
          marginBottom: 40,
        }}
      >
        {/* GitHub icon */}
        <svg width="40" height="40" viewBox="0 0 24 24" fill={colors.white}>
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
        </svg>
        <span
          style={{
            fontSize: 30,
            color: colors.white,
            fontFamily: fonts.sans,
            fontWeight: 500,
          }}
        >
          github.com/kimimgo/viznoir
        </span>
      </div>

      {/* License badge */}
      <div
        style={{
          opacity: licenseOpacity,
          display: "flex",
          gap: 24,
          alignItems: "center",
        }}
      >
        <div
          style={{
            padding: "8px 24px",
            borderRadius: 999,
            backgroundColor: colors.green + "20",
            border: `1px solid ${colors.green}`,
            color: colors.green,
            fontSize: 20,
            fontFamily: fonts.sans,
            fontWeight: 600,
          }}
        >
          MIT License
        </div>
        <div
          style={{
            padding: "8px 24px",
            borderRadius: 999,
            backgroundColor: colors.accent + "20",
            border: `1px solid ${colors.accent}`,
            color: colors.accent,
            fontSize: 20,
            fontFamily: fonts.sans,
            fontWeight: 600,
          }}
        >
          Open Source
        </div>
      </div>
    </AbsoluteFill>
  );
};
