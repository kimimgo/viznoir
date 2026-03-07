import {
  AbsoluteFill,
  Img,
  interpolate,
  useCurrentFrame,
  spring,
  useVideoConfig,
  staticFile,
} from "remotion";
import { colors, fonts, fullScreen, terminalBox } from "../styles";

const showcaseImages = [
  { src: staticFile("showcase/aero_cylinder.png"), label: "CFD Pressure Field" },
  { src: staticFile("showcase/ct_head_contour.png"), label: "Medical Contour" },
  { src: staticFile("showcase/mcp_slice.png"), label: "Slice Analysis" },
  { src: staticFile("showcase/mcp_streamlines.png"), label: "Flow Streamlines" },
];

const conversation = [
  { role: "user" as const, text: 'Render the pressure field of my CFD simulation' },
  { role: "ai" as const, text: 'Rendering with viznoir...' },
];

export const SceneDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Phase 1: Terminal conversation (0-180)
  const msg1Chars = Math.min(
    Math.floor(interpolate(frame, [10, 70], [0, conversation[0].text.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })),
    conversation[0].text.length
  );

  const msg2Opacity = interpolate(frame, [90, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const msg2Chars = Math.min(
    Math.floor(interpolate(frame, [100, 140], [0, conversation[1].text.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })),
    conversation[1].text.length
  );

  // Phase 2: Image gallery (150-540)
  const galleryStart = 150;
  const imgDuration = 90; // 3 seconds per image

  const currentImageIndex = Math.min(
    Math.floor(Math.max(0, frame - galleryStart) / imgDuration),
    showcaseImages.length - 1
  );

  const imageLocalFrame = Math.max(0, frame - galleryStart - currentImageIndex * imgDuration);

  const imgOpacity = interpolate(imageLocalFrame, [0, 15, imgDuration - 15, imgDuration], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const imgScale = spring({
    frame: imageLocalFrame,
    fps,
    from: 0.95,
    to: 1,
    durationInFrames: 20,
  });

  const showGallery = frame >= galleryStart;

  return (
    <AbsoluteFill style={fullScreen}>
      {/* Terminal conversation */}
      {!showGallery && (
        <div style={{ ...terminalBox, maxWidth: 1200 }}>
          {/* User message */}
          <div style={{ marginBottom: 20 }}>
            <span style={{ color: colors.accent, fontWeight: 600 }}>User: </span>
            <span style={{ color: colors.white }}>
              {conversation[0].text.slice(0, msg1Chars)}
            </span>
          </div>

          {/* AI response */}
          <div style={{ opacity: msg2Opacity }}>
            <span style={{ color: colors.green, fontWeight: 600 }}>AI: </span>
            <span style={{ color: colors.gray }}>
              {conversation[1].text.slice(0, msg2Chars)}
            </span>
          </div>
        </div>
      )}

      {/* Image gallery */}
      {showGallery && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 24,
            opacity: imgOpacity,
            transform: `scale(${imgScale})`,
          }}
        >
          <Img
            src={showcaseImages[currentImageIndex].src}
            style={{
              maxWidth: 1400,
              maxHeight: 800,
              borderRadius: 16,
              border: `2px solid ${colors.dim}`,
              objectFit: "contain",
            }}
          />
          <div
            style={{
              fontSize: 32,
              color: colors.gray,
              fontFamily: fonts.sans,
              fontWeight: 500,
            }}
          >
            {showcaseImages[currentImageIndex].label}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
