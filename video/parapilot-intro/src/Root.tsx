import { Composition } from "remotion";
import { ViznoirIntro } from "./ViznoirIntro";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="viznoir-intro"
      component={ViznoirIntro}
      durationInFrames={30 * 55}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
