// 작성 중인 내용이 있을 때 다른 화면으로 이동하거나 탭을 닫으면 확인을 받는다.
//   useLeaveGuard(isDirty);

import { useEffect } from "react";
import { useBlocker } from "react-router";
import { useDialog } from "./Dialog";

export function useLeaveGuard(when: boolean, message = "저장하지 않은 내용이 사라집니다.") {
  const { confirmDialog } = useDialog();
  const blocker = useBlocker(when);

  // 앱 안에서의 이동 (메뉴, 링크, 뒤로 가기)
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    confirmDialog({ title: "이 화면을 떠날까요?", message, confirmText: "떠나기", danger: true }).then((ok) =>
      ok ? blocker.proceed() : blocker.reset(),
    );
  }, [blocker, confirmDialog, message]);

  // 탭 닫기, 새로고침, 주소 직접 입력 (브라우저 기본 확인창만 가능)
  useEffect(() => {
    if (!when) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [when]);
}
