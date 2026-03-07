import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  spring,
  useVideoConfig,
} from "remotion";
import { colors, fonts, fullScreen, terminalBox } from "../styles";

export const SceneSolution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const logoScale = spring({
    frame,
    fps,
    from: 0.5,
    to: 1,
    durationInFrames: 30,
  });

  const subtitleY = spring({
    frame: frame - 30,
    fps,
    from: 30,
    to: 0,
    durationInFrames: 25,
  });

  const subtitleOpacity = interpolate(frame, [30, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Terminal typing animation
  const pipCommand = "pip install mcp-server-viznoir";
  const terminalOpacity = interpolate(frame, [80, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const charsVisible = Math.min(
    Math.floor(interpolate(frame, [100, 160], [0, pipCommand.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })),
    pipCommand.length
  );

  const fadeOut = interpolate(frame, [180, 210], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ ...fullScreen, opacity: fadeOut }}>
      {/* Logo / Title */}
      <div
        style={{
          opacity: fadeIn,
          transform: `scale(${logoScale})`,
          textAlign: "center",
          marginBottom: 20,
        }}
      >
        <div
          style={{
            fontSize: 80,
            fontWeight: 800,
            letterSpacing: -2,
            fontFamily: fonts.sans,
          }}
        >
          <span style={{ color: colors.accent }}>para</span>
          <span style={{ color: colors.white }}>pilot</span>
        </div>
      </div>

      {/* Subtitle */}
      <div
        style={{
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
          fontSize: 32,
          color: colors.gray,
          fontFamily: fonts.sans,
          textAlign: "center",
          marginBottom: 60,
        }}
      >
        Headless CAE post-processing for AI assistants
      </div>

      {/* Terminal */}
      <div style={{ ...terminalBox, opacity: terminalOpacity }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ color: colors.green }}>$</span>
          <span style={{ color: colors.white }}>
            {pipCommand.slice(0, charsVisible)}
          </span>
          {charsVisible < pipCommand.length && (
            <span
              style={{
                display: "inline-block",
                width: 14,
                height: 28,
                backgroundColor: colors.white,
                animation: "blink 1s step-end infinite",
              }}
            />
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
