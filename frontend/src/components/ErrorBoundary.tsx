// 화면을 그리다 에러가 나도 앱 전체가 하얗게 멈추지 않도록 막는다.
// resetKey(보통 현재 경로)가 바뀌면 에러 상태를 풀어서, 다른 메뉴로 이동하면 다시 정상 동작한다.

import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  resetKey?: string;
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("화면 오류", error, info.componentStack);
  }

  componentDidUpdate(prev: Props) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="card error-screen" role="alert">
        <h2>화면을 표시하는 중 문제가 발생했습니다</h2>
        <p className="muted">잠시 후 다시 시도해 주세요. 문제가 계속되면 관리자에게 알려주세요.</p>
        <pre className="error-detail">{this.state.error.message}</pre>
        <div className="actions">
          <button onClick={() => this.setState({ error: null })}>다시 시도</button>
          <button className="primary" onClick={() => window.location.reload()}>
            새로고침
          </button>
        </div>
      </div>
    );
  }
}
