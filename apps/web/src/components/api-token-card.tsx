import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, KeyRound, Plus, RefreshCw, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ApiTokenList } from "@/lib/types";

/**
 * 🔑 توکنِ دسترسیِ ربات (وصلهٔ ما)
 *
 * ادمین اینجا یک توکن می‌سازد و همان را به رباتِ تلگرام می‌دهد. آدرسِ عمومیِ همین
 * پنل داخلِ خودِ توکن است، پس ربات نه آدرس می‌پرسد و نه نام‌کاربری/رمز.
 * راز فقط یک‌بار نشان داده می‌شود (در دیتابیس فقط hash می‌مانَد).
 */
export function ApiTokenCard() {
  const toast = useToast();
  const { t } = useI18n();
  const qc = useQueryClient();

  const { data } = useQuery<ApiTokenList>({ queryKey: ["api-tokens"], queryFn: api.listApiTokens });
  const [name, setName] = React.useState("telegram-bot");
  const [fresh, setFresh] = React.useState("");
  const [copied, setCopied] = React.useState(false);

  const createMut = useMutation({
    mutationFn: () => api.createApiToken(name.trim() || "bot"),
    onSuccess: (res) => {
      setFresh(res.token);
      setCopied(false);
      toast.push("success", t("apiTokenCreated"));
      qc.invalidateQueries({ queryKey: ["api-tokens"] });
    },
    onError: (e: Error) => toast.push("error", e.message),
  });

  const revokeMut = useMutation({
    mutationFn: (id: number) => api.revokeApiToken(id),
    onSuccess: () => {
      toast.push("success", t("apiTokenRevoked"));
      qc.invalidateQueries({ queryKey: ["api-tokens"] });
    },
    onError: (e: Error) => toast.push("error", e.message),
  });

  const copy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.push("error", "clipboard blocked — select and copy manually");
    }
  };

  const fmt = (ms: number) => (ms ? new Date(ms).toLocaleString() : "—");
  const tokens = data?.tokens || [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-main" />
          <CardTitle>{t("apiTokenSection")}</CardTitle>
        </div>
        <CardDescription>{t("apiTokenSectionDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
          <div className="space-y-2">
            <Label htmlFor="api-token-name">{t("apiTokenName")}</Label>
            <Input
              id="api-token-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="telegram-bot"
              autoComplete="off"
            />
          </div>
          <div className="flex items-end">
            <Button className="w-full sm:w-auto" onClick={() => createMut.mutate()} disabled={createMut.isPending}>
              <Plus className="h-4 w-4" />
              {createMut.isPending ? t("apiTokenCreating") : t("apiTokenCreate")}
            </Button>
          </div>
        </div>

        {fresh && (
          <div className="space-y-2 rounded-base border-2 border-main bg-main/10 p-3">
            <div className="text-sm font-heading">{t("apiTokenShownOnce")}</div>
            <div className="flex gap-2">
              <Input readOnly value={fresh} className="font-mono text-xs" onFocus={(e) => e.currentTarget.select()} />
              <Button variant="neutral" size="icon" onClick={() => copy(fresh)} title={t("copy")}>
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-[11px] text-text/60">{t("apiTokenHowTo")}</p>
          </div>
        )}

        <div className="space-y-2">
          {tokens.length === 0 && (
            <p className="text-sm text-text/60">{t("apiTokenEmpty")}</p>
          )}
          {tokens.map((tk) => (
            <div
              key={tk.id}
              className="flex flex-col gap-2 rounded-base border-2 border-border bg-bg/40 p-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="space-y-1">
                <div className="font-heading text-sm">
                  {tk.name || "bot"}{" "}
                  <span className="font-base text-text/50">
                    #{tk.id} · {tk.prefix}…
                  </span>
                  {tk.revokedAt ? (
                    <span className="ml-2 rounded-base bg-danger/20 px-2 py-0.5 text-[11px] text-danger">
                      {t("apiTokenRevokedTag")}
                    </span>
                  ) : (
                    <span className="ml-2 rounded-base bg-success/20 px-2 py-0.5 text-[11px]">
                      {t("apiTokenActiveTag")}
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-text/55">
                  {t("apiTokenCreatedAt")}: {fmt(tk.createdAt)} · {t("apiTokenLastUsed")}: {fmt(tk.lastUsedAt)} ·{" "}
                  {t("apiTokenCalls")}: {tk.usedCount}
                </div>
              </div>
              <div className="flex gap-2">
                {tk.revokedAt ? (
                  <Button variant="neutral" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ["api-tokens"] })}>
                    <RefreshCw className="h-4 w-4" />
                    {t("refresh")}
                  </Button>
                ) : (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => revokeMut.mutate(tk.id)}
                    disabled={revokeMut.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                    {t("apiTokenRevoke")}
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>

        <p className="text-[11px] text-text/50">
          {t("apiTokenHint")}
          {data?.url ? ` (${data.url})` : ""}
        </p>
      </CardContent>
    </Card>
  );
}
