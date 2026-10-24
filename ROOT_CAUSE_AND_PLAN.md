# XCover5 iOS 포팅: 원인 조사, 수정, 다음 계획

작성: 2026-10-24. 목표는 원인에 근거한 수정이며, 진단 이미지의 연속 설치 자체를 진척으로 계산하지 않는다.

## 현재 상태

- 자체 XNU 커널, 내부 eMMC 읽기, HFS 마운트, Mach-O 실행, 원본 Apple dyld와 캐시, libSystem, pthread, Mach IPC까지 실기기 증거가 있다.
- Apple launchd가 PID1로 초기화한 실행도 있으나 안정적이지 않다. 자체 RunAtLoad 작업의 M35 JOB PASS는 아직 없다.
- 두 실패는 분리한다: (A) 간헐적 사용자 코드/launchd 초기화 정체, (B) xpcproxy의 SIGKILL.
- CS flags0x01000001은 VALID|KILLED다. 이것만으로 페이지 해시 손상 또는 특정 플랫폼 거부를 확정할 수 없다. 종료 reason0도 여전히 미해결이다.

## 확인된 문제와 이번 수정

### 네이티브 iOS에 macOS 시뮬레이터 실행 정책 적용

빌드는 macOS SDK를 사용해 XNU_TARGET_OS_OSX가 켜진다. kern_exec.c의 process_signature는 iOS 바이너리에 psa_platform=IOS 또는 개발용 우회/특정 entitlement를 요구한다. 자체 시험 프로그램들은 platform2를 명시했으므로 이 호환성 문제를 가릴 수 있었다.

원본 xpcproxy는 LC_BUILD_VERSION iOS16.5, LC_MAIN0x500c이며 /usr/lib/dyld와 libSystem/libobjc를 사용한다. 로컬 디스어셈블의 직접 spawnattr 호출에는 플랫폼 setter가 보이지 않았다. 이것은 해당 바이너리의 정적 관찰이고, 부모 launchd/libxpc가 실제 전달한 속성이나 실기기 SIGKILL 원인을 증명하지 않는다.

수정0044: ARM64_BOARD_CONFIG_SWEET에서 iOS 실행의 플랫폼 속성이 없거나0이면 네이티브 실행 기본값으로 허용한다. 명시적으로 다른 플랫폼을 지정하면 계속 거부한다. 비SWEET 및 비iOS 경로, 코드서명 검증, 페이지 검증, entitlement 부여 정책은 바꾸지 않는다. 허용 경로에는 XCOVER5 NATIVE IOS 로그를 남긴다.

검증: 실제 패치된 소스 구간을 추출해 SWEET/desktop의 development/release 및 native-iOS 조건으로 컴파일한다. 각각40조합, 총200경우가 통과했다. 이는 실행 허용 정책 검사이며 전체 exec/ABI/하드웨어 검증은 아니다. CI에서도 실제 빌드 소스로 같은 검사를 실행한다.

### 과도한 반복 플래싱과 읽기 어려운 로그

M35F부터 이미 통과한 회귀 실행을 생략한 빠른 경로를 사용한다. M18/M19/M20, 캐시 마운트 및 M34 성공 게이트는 유지한다. M35G는 LOAD/SIGN/PAGE/MARK 기록을 보관해 마지막 CS_KILLED 종료 때 다시 출력한다. 새 이미지가 원인 수정인지 진단용인지를 구분해 기록한다.

## 아직 확정하지 못한 문제

- 간헐적 정체가 스케줄러, 사용자 공간 락, 파일 페이지인, 콘솔 출력 중 어디에서 발생하는지 미확정이다.
- eMMC는 섹터마다 FIFO reset/CMD17/PIO 대기를 수행하므로 큰 cold page-in 비용이 있다. 하지만 media_lock 및 지역 버퍼가 있고, 동시 읽기 손상은 확인되지 않았다. 성능 한계와 영구 정체를 같은 원인이라고 단정하지 않는다.
- 현재 AMFI 대체 구현은 entitlement를 제공하지 않는다. 기본 작업 실행을 넘는 서비스가 이를 요구할 가능성이 있으며 별도 기능 작업이다.
- 원본 Apple GUI, 그래픽 가속, 터치, 통신 등은 아직 검증되지 않았다.

## 다음 작업과 통과 기준

| 순서 | 작업 | 진행/종료 조건 |
|---|---|---|
| 1 | 네이티브 실행 정책 수정, 실제 커널 컴파일, 파일 검증 | 200정책검사, CI 성공, 서명/페이지 검사 유지, boot-only 패키지 및 HFS 소유권 검증 |
| 2 | 수정된 원본 launchd 경로를 한 번 통제 검증 | NATIVE IOS 경로 여부, xpcproxy 실행/종료 기록, M35 JOB PASS 확인. 성공해도 전체 iOS 부팅이라고 부르지 않음 |
| 3A | SIGKILL이 남으면 마지막 SNAP의 실제 원인 수정 | SIGN/PAGE/MARK와 파일/코드를 근거로 재현 및 회귀검사. 근거 없는 서명 강제 허용 금지 |
| 3B | 정체가 남으면 실행/대기 상태 수집 | 마지막 완료단계와 해당 프로세스·스레드의 대기상태 확보. 같은 이미지 반복 설치로 원인 추정하지 않음 |
| 4 | 최소 launchd 안정성 및 bootstrap 검증 | 동일 이미지3회 부팅에서 단일 자체 작업 성공, bootstrap 등록/조회/요청-응답, PID1 생존 확인 |
| 5 | 최소 실제 시스템 서비스 구성 | 필요한 서비스 하나씩, 의존성/entitlement/파일 경로/재시작 검증. 전체 stock daemon 일괄 활성화 금지 |
| 6 | Objective-C/Foundation 및 기본 XPC 기능 | 간단한 실제 프레임워크 프로그램이 파일·메모리·스레드·IPC를 검증하고 정상 종료 |
| 7 | 화면·입력 경로 개발 | 먼저 단순 framebuffer 화면과 터치 이벤트. 이후 GUI 서비스와 렌더링 의존성 검토. GPU/전체 SpringBoard 가능 여부 별도 평가 |

## 실행 원칙과 일정

- 이번 수정은 소스로 확인된 정책 불일치를 고친다. 관측된 모든 SIGKILL/정체가 해결됐다는 뜻이 아니다.
- 호스트 검사와 하드웨어 통과를 분리해 기록한다. 변경 이유, 기대 로그, 실패 시 다음 분기를 먼저 정한 뒤 설치본을 만든다.
- 다음 설치는 위1번 검증을 끝낸 산출물 한 개로 한다. 불확실한 변경 여러 개를 섞지 않는다.
- 시간 대신 통과 기준으로 단계 이동한다. iOS 홈 화면 완료 날짜는 현재 근거로 산정할 수 없으며7번에는 아직 큰 하드웨어 작업이 남아 있다.
- 산출물은 프로젝트 xcover5/artifacts 아래에만 저장한다. 사용자가 Odin을 수동 실행한다. userdata/cache는 이번 변경에서 쓰지 않는다.

## 증거 위치

- xcover5/research/launchd-rootcause/xpcproxy-info.txt 및 xpcproxy-disass.txt: ipsw 로컬 정적 관찰. REA는 원본 해시를 식별했으나 연결된 디컴파일 provider 부재로 함수 분석은 불가했다. 정적 분석이 실행을 관찰했다고 주장하지 않는다.
- tools/test_native_ios_policy.py: 실제 소스 정책 추출 검사.
- xnu/patches/0044-sweet-native-ios-spawn-default.patch: 좁은 보드 전용 수정.
- 이전 실기기 영상 분석은 xcover5/artifacts/m35*/video-*/review.txt.
