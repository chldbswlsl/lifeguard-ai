"""실제 브라우저로 화면을 조작하는 테스트. seed 데이터(관리자, 보호자, 어르신 A/B/C × 28일)를 기준으로 한다."""

import datetime as dt
import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

ADMIN = ("admin@lifeguard.dev", "admin1234")
GUARDIAN = ("guardian@lifeguard.dev", "guardian1234")


def login(page: Page, email: str, password: str) -> None:
    page.goto("/login")
    page.get_by_label("이메일").fill(email)
    page.locator("input[autocomplete=current-password]").fill(password)
    page.get_by_role("button", name="로그인", exact=True).click()


def rows(page: Page):
    return page.locator("table.table tbody tr")


def open_senior(page: Page, name: str) -> None:
    page.get_by_label(f"{name} 상세 보기").click()
    expect(page.get_by_role("heading", level=1)).to_contain_text(name)


def test_틀린_비밀번호는_안내하고_로그인되지_않는다(page: Page):
    login(page, ADMIN[0], "wrongpass1")
    expect(page.get_by_role("alert")).to_have_text("이메일 또는 비밀번호가 올바르지 않습니다")
    expect(page).to_have_url(re.compile(r"/login$"))


def test_관리자는_전체_어르신과_현황을_본다(page: Page):
    login(page, *ADMIN)
    expect(page.get_by_role("heading", name="전체 어르신 관리")).to_be_visible()
    expect(rows(page)).to_have_count(3)
    expect(page.locator(".stat").first).to_contain_text("3명")
    expect(page.locator(".badge.admin")).to_have_text("관리자")


def test_보호자는_담당_어르신만_보고_다른_어르신은_열_수_없다(page: Page):
    login(page, *GUARDIAN)
    expect(page.get_by_role("heading", name="담당 어르신")).to_be_visible()
    expect(rows(page)).to_have_count(1)
    expect(rows(page).first).to_contain_text("A 어르신")
    expect(page.locator(".stats")).to_have_count(0)  # 현황 카드는 관리자만

    page.goto("/seniors/2")
    expect(page.locator(".error")).to_have_text("어르신 정보를 찾을 수 없습니다")


def test_생활_기록을_입력하고_같은_날짜는_덮어쓰기_확인을_받는다(page: Page):
    login(page, *ADMIN)
    open_senior(page, "C 어르신")
    expect(rows(page).first).to_be_visible()
    before = rows(page).count()  # 화면은 오늘 포함 최근 28일, seed는 어제까지 → 27건

    # 오늘 기록 새로 입력
    page.get_by_role("button", name="+ 기록 입력").click()
    page.get_by_label("기상 시각").fill("07:30")
    page.get_by_label("식사 시각").fill("8:00, 12:30")
    page.get_by_label("외출 시간").fill("45")
    page.get_by_role("button", name="저장", exact=True).click()
    expect(page.locator(".toast")).to_contain_text("기록을 저장했습니다")
    expect(rows(page)).to_have_count(before + 1)
    today = dt.date.today().isoformat()
    expect(rows(page).first).to_contain_text(today)
    expect(rows(page).first).to_contain_text("2회")  # 식사 횟수는 시각 개수로 자동 계산

    # 같은 날짜로 다시 입력하면 확인창
    page.get_by_role("button", name="+ 기록 입력").click()
    page.get_by_label("기상 시각").fill("09:00")
    page.get_by_role("button", name="저장", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("이미 기록이 있습니다")
    dialog.get_by_role("button", name="취소").click()
    expect(dialog).to_have_count(0)
    expect(rows(page)).to_have_count(before + 1)


def test_잘못된_입력은_칸_아래에_안내한다(page: Page):
    login(page, *ADMIN)
    open_senior(page, "C 어르신")
    page.get_by_role("button", name="+ 기록 입력").click()
    page.get_by_label("식사 시각").fill("25:00")
    page.get_by_label("시간대별 활동량").fill("1, 2, 3")
    page.get_by_role("button", name="저장", exact=True).click()
    expect(page.locator(".field-error")).to_have_count(2)
    expect(page.locator(".field-error").nth(0)).to_contain_text("25:00")
    expect(page.locator(".field-error").nth(1)).to_contain_text("24개")


def test_작성_중에_다른_화면으로_가면_확인을_받는다(page: Page):
    login(page, *ADMIN)
    open_senior(page, "B 어르신")
    page.get_by_role("button", name="+ 기록 입력").click()
    page.get_by_label("메모").fill("작성 중인 메모")

    page.get_by_role("link", name="어르신 목록").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("이 화면을 떠날까요?")
    dialog.get_by_role("button", name="취소").click()
    expect(page.get_by_label("메모")).to_have_value("작성 중인 메모")  # 그대로 남아 있다

    page.get_by_role("link", name="어르신 목록").click()
    page.get_by_role("dialog").get_by_role("button", name="떠나기").click()
    expect(page.get_by_role("heading", name="전체 어르신 관리")).to_be_visible()


def test_관리자는_어르신을_등록하고_삭제할_수_있다(page: Page):
    login(page, *ADMIN)
    page.get_by_role("button", name="+ 어르신 등록").click()
    page.get_by_label("이름").fill("E2E 어르신")
    page.get_by_label("출생연도").fill("1950")
    page.get_by_role("button", name="등록").click()
    expect(page.get_by_role("heading", level=1)).to_contain_text("E2E 어르신")
    expect(page.locator(".card.empty")).to_contain_text("기록이 없습니다")

    page.get_by_role("button", name="삭제", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("되돌릴 수 없습니다")
    dialog.get_by_role("button", name="삭제").click()
    expect(page.locator(".toast")).to_contain_text("삭제했습니다")
    expect(page.get_by_role("heading", name="전체 어르신 관리")).to_be_visible()
    expect(rows(page)).to_have_count(3)


def test_관리자는_보호자를_연결하고_해제할_수_있다(page: Page):
    login(page, *ADMIN)
    open_senior(page, "B 어르신")
    expect(page.locator(".guardian-row")).to_have_count(0)

    page.get_by_label("연결할 보호자 이메일").fill(GUARDIAN[0])
    page.get_by_role("button", name="연결", exact=True).click()
    expect(page.locator(".guardian-row")).to_have_count(1)
    expect(page.locator(".guardian-row")).to_contain_text("김보호")

    page.locator(".guardian-row").get_by_role("button", name="해제").click()
    page.get_by_role("dialog").get_by_role("button", name="연결 해제").click()
    expect(page.locator(".guardian-row")).to_have_count(0)


def test_회원가입은_비밀번호_규칙을_안내하고_가입하면_로그인된다(page: Page):
    page.goto("/signup")
    page.get_by_label("이름").fill("새보호자")
    page.get_by_label("이메일").fill("newguardian@test.dev")
    pw = page.locator("input[autocomplete=new-password]")
    pw.nth(0).fill("abcdefgh")
    pw.nth(1).fill("abcdefgh")
    page.get_by_role("button", name="가입하기").click()
    expect(page.locator(".field-error")).to_contain_text("영문과 숫자")

    # 보기 버튼으로 입력한 비밀번호를 확인할 수 있다
    page.get_by_role("button", name="비밀번호 보기").first.click()
    expect(pw.nth(0)).to_have_attribute("type", "text")

    pw.nth(0).fill("newpass123")
    pw.nth(1).fill("newpass123")
    page.get_by_role("button", name="가입하기").click()
    expect(page.get_by_role("heading", name="담당 어르신")).to_be_visible()
    expect(page.locator(".card.empty")).to_contain_text("등록된 어르신이 없습니다")


def test_로그인이_만료되면_로그인_화면으로_돌아간다(page: Page):
    login(page, *ADMIN)
    expect(page.get_by_role("heading", name="전체 어르신 관리")).to_be_visible()
    # 서버가 거절할 토큰으로 바꿔치기 → 다음 API 호출에서 401
    page.evaluate("localStorage.setItem('lifeguard_token', 'invalid.token.value')")
    page.get_by_label("A 어르신 상세 보기").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.locator(".notice")).to_have_text("로그인이 만료되었습니다. 다시 로그인해 주세요")


def test_로그아웃하면_저장된_정보가_지워진다(page: Page):
    login(page, *GUARDIAN)
    expect(page.get_by_role("heading", name="담당 어르신")).to_be_visible()
    page.get_by_role("link", name="로그아웃").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    assert page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('lifeguard_')).length") == 0
    page.goto("/")
    expect(page).to_have_url(re.compile(r"/login$"))
