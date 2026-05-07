import { ObservatoryScreen } from "@/components/observatory/observatory-screen";
import { OBSERVATORY_MODEL } from "@/lib/observatory";

export const dynamic = "force-static";

export default function ObservePage(): JSX.Element {
  return <ObservatoryScreen model={OBSERVATORY_MODEL} />;
}
