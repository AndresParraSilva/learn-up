export type TopicImportReport = {
  topic_slug: string;
  archive_format: string;
  source_app_version: string;
  destination_app_version: string;
  mode: "new" | "update";
  status: "validated" | "installed";
  installed: string[];
  replaced: string[];
  merged_q_and_a: number;
  skipped_q_and_a: string[];
  ignored: string[];
  backup: string | null;
  trust_warning: string;
};

async function responseError(response: Response): Promise<Error> {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return new Error(
    body?.detail ?? `Topic transfer failed with HTTP ${response.status}`,
  );
}

export async function downloadTopic(topicSlug: string): Promise<void> {
  const response = await fetch(
    `/api/t/${encodeURIComponent(topicSlug)}/export`,
  );
  if (!response.ok) throw await responseError(response);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${topicSlug}.learnup.zip`;
  link.click();
  URL.revokeObjectURL(url);
}

async function sendArchive(
  file: File,
  confirm: boolean,
): Promise<TopicImportReport> {
  const params = new URLSearchParams({
    dry_run: String(!confirm),
    confirm: String(confirm),
  });
  const response = await fetch(`/api/topics/import?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/zip" },
    body: file,
  });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as TopicImportReport;
}

export function validateTopicArchive(file: File): Promise<TopicImportReport> {
  return sendArchive(file, false);
}

export function importTopicArchive(file: File): Promise<TopicImportReport> {
  return sendArchive(file, true);
}
