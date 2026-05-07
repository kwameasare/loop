import { ReplayWorkbench } from "@/components/replay/replay-workbench";
import { getReplayWorkbenchModel } from "@/lib/replay-workbench";

export const dynamic = "force-static";

export default function ReplayPage(): JSX.Element {
  return <ReplayWorkbench model={getReplayWorkbenchModel()} />;
}
