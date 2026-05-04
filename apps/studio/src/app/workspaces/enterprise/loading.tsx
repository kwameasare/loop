import { SectionLoading } from "@/components/section-states";

export default function WorkspaceEnterpriseLoading() {
  return (
    <SectionLoading
      title="Enterprise SSO"
      subtitle="Loading SAML configuration…"
    />
  );
}
