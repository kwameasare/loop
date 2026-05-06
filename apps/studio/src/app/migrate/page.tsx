import { MigrationScreen } from "@/components/migration";

export const dynamic = "force-static";

export const metadata = {
  title: "Migration Atelier · Loop Studio",
  description:
    "Bring an agent into Loop with verified or planned import paths, parity proof, and a rollback route.",
};

export default function MigratePage() {
  return <MigrationScreen />;
}
