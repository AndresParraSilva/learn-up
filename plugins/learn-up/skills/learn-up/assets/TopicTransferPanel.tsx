import { useState } from "react";

import {
  downloadTopic,
  importTopicArchive,
  type TopicImportReport,
  validateTopicArchive,
} from "../api/topicTransfer";

const TRUST_WARNING =
  "Import learn-up topics only from people and sources you trust. Validation reduces common archive risks, but it cannot make an untrusted archive safe.";

type Props = {
  topicSlug?: string;
  onImported?: (topicSlug: string) => void | Promise<void>;
};

export function TopicTransferPanel({ topicSlug, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<TopicImportReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="panel topic-transfer"
      aria-labelledby="topic-transfer-title"
    >
      <h2 id="topic-transfer-title">Share a topic</h2>
      <p className="disclaimer">{TRUST_WARNING}</p>
      {topicSlug && (
        <button
          disabled={busy}
          onClick={() => void run(() => downloadTopic(topicSlug))}
        >
          Export this topic
        </button>
      )}
      <label className="field__label" htmlFor="topic-archive">
        Topic archive
      </label>
      <input
        id="topic-archive"
        type="file"
        accept=".zip,.learnup.zip,application/zip"
        disabled={busy}
        onChange={(event) => {
          setFile(event.target.files?.[0] ?? null);
          setReport(null);
          setError(null);
        }}
      />
      <button
        disabled={busy || file === null}
        onClick={() =>
          void run(async () => {
            if (file === null) return;
            setReport(await validateTopicArchive(file));
          })
        }
      >
        Validate archive
      </button>
      {report && (
        <div role="status" className="topic-transfer__report">
          <p>
            <strong>{report.topic_slug}</strong> is a {report.mode} from app
            version {report.source_app_version}. Archive format{" "}
            {report.archive_format} is compatible with this app (
            {report.destination_app_version}).
          </p>
          <p>
            Q&amp;A to merge: {report.merged_q_and_a}. Ignored files:{" "}
            {report.ignored.length}. Skipped Q&amp;A:{" "}
            {report.skipped_q_and_a.length}.
          </p>
          {report.status === "validated" && (
            <button
              disabled={busy || file === null}
              onClick={() =>
                void run(async () => {
                  if (file === null) return;
                  const installed = await importTopicArchive(file);
                  setReport(installed);
                  await onImported?.(installed.topic_slug);
                })
              }
            >
              Confirm{" "}
              {report.mode === "update" ? "topic update" : "topic import"}
            </button>
          )}
          {report.backup && <p>Backup: {report.backup}</p>}
        </div>
      )}
      {error && <p className="error-banner">{error}</p>}
    </section>
  );
}
