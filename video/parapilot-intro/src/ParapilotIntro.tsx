import { AbsoluteFill, Series } from "remotion";
import { SceneProblem } from "./scenes/SceneProblem";
import { SceneSolution } from "./scenes/SceneSolution";
import { SceneDemo } from "./scenes/SceneDemo";
import { SceneFeatures } from "./scenes/SceneFeatures";
import { SceneCTA } from "./scenes/SceneCTA";

export const ViznoirIntro: React.FC = () => {
  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={5 * 30}>
          <SceneProblem />
        </Series.Sequence>
        <Series.Sequence durationInFrames={7 * 30}>
          <SceneSolution />
        </Series.Sequence>
        <Series.Sequence durationInFrames={18 * 30}>
          <SceneDemo />
        </Series.Sequence>
        <Series.Sequence durationInFrames={15 * 30}>
          <SceneFeatures />
        </Series.Sequence>
        <Series.Sequence durationInFrames={10 * 30}>
          <SceneCTA />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
