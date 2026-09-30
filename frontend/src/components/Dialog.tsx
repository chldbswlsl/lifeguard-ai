// window.confirm / alert 대신 쓰는 확인창과 알림(toast).
//
//   const { confirmDialog, alertDialog, toast } = useDialog();
//   if (!(await confirmDialog({ title: "삭제할까요?", message: "…", confirmText: "삭제", danger: true }))) return;
//   toast("저장했습니다");  toast("실패했습니다", "error");

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

interface ConfirmOptions {
  title: string;
  message?: ReactNode;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

interface DialogState extends ConfirmOptions {
  alertOnly: boolean;
  resolve: (ok: boolean) => void;
}

interface Toast {
  id: number;
  text: string;
  kind: "success" | "error";
}

interface DialogApi {
  confirmDialog: (opts: ConfirmOptions) => Promise<boolean>;
  alertDialog: (opts: Omit<ConfirmOptions, "cancelText" | "danger">) => Promise<void>;
  toast: (text: string, kind?: Toast["kind"]) => void;
}

const DialogContext = createContext<DialogApi | null>(null);

export function DialogProvider({ children }: { children: ReactNode }) {
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const confirmDialog = useCallback(
    (opts: ConfirmOptions) => new Promise<boolean>((resolve) => setDialog({ ...opts, alertOnly: false, resolve })),
    [],
  );
  const alertDialog = useCallback(
    (opts: ConfirmOptions) =>
      new Promise<void>((resolve) => setDialog({ ...opts, alertOnly: true, resolve: () => resolve() })),
    [],
  );
  const toast = useCallback((text: string, kind: Toast["kind"] = "success") => {
    const id = ++nextId.current;
    setToasts((ts) => [...ts, { id, text, kind }]);
    setTimeout(() => setToasts((ts) => ts.filter((t) => t.id !== id)), 3000);
  }, []);

  const close = (ok: boolean) => {
    dialog?.resolve(ok);
    setDialog(null);
  };

  // ESC로 닫기
  useEffect(() => {
    if (!dialog) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        dialog.resolve(false);
        setDialog(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dialog]);

  return (
    <DialogContext value={{ confirmDialog, alertDialog, toast }}>
      {children}
      {dialog && (
        <div className="dialog-backdrop" onClick={() => close(false)}>
          <div
            className="dialog card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dialog-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="dialog-title">{dialog.title}</h3>
            {dialog.message && <div className="dialog-message">{dialog.message}</div>}
            <div className="actions">
              {!dialog.alertOnly && <button onClick={() => close(false)}>{dialog.cancelText ?? "취소"}</button>}
              <button className={dialog.danger ? "primary danger-fill" : "primary"} onClick={() => close(true)} autoFocus>
                {dialog.confirmText ?? "확인"}
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>
            {t.text}
          </div>
        ))}
      </div>
    </DialogContext>
  );
}

export function useDialog(): DialogApi {
  const ctx = useContext(DialogContext);
  if (!ctx) throw new Error("useDialog는 DialogProvider 안에서만 사용할 수 있습니다");
  return ctx;
}
