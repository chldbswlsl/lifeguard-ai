import { useState, type InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  /** 로그인: current-password, 가입·변경: new-password (브라우저 비밀번호 관리자가 올바르게 동작하도록) */
  autoComplete: "current-password" | "new-password";
};

export default function PasswordInput(props: Props) {
  const [visible, setVisible] = useState(false);
  return (
    <span className="password-input">
      <input {...props} type={visible ? "text" : "password"} />
      <button
        type="button"
        className="link"
        tabIndex={-1}
        onClick={() => setVisible((v) => !v)}
        title={visible ? "숨기기" : "보기"}
        aria-label={visible ? "비밀번호 숨기기" : "비밀번호 보기"}
      >
        {visible ? "숨기기" : "보기"}
      </button>
    </span>
  );
}
