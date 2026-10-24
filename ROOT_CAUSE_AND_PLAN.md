# XCover5 iOS 포팅: 원인 조사, 수정, 다음 계획

작성: 2026-10-24. 목표는 원인에 근거한 수정이며, 진단 이미지의 연속 설치 자체를 진척으로 계산하지 않는다.

## 현재 상태

- 자체 XNU 커널, 내부 eMMC 읽기, HFS 마운트, Mach-O 실행, 원본 Apple dyld와 캐시, libSystem, pthread, Mach IPC까지 실기기 증거가 있다.
- M35H에서 Apple launchd가 자체 RunAtLoad 작업을 실행해 M35 JOB PASS 및 정상 종료0을 확인했다. 단일 부팅 성공이며 반복 안정성은 아직 미검증이다.
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

## 이번 산출물 검증 결과

- CI40089586743 성공. 실제 패치된 커널 소스 정책200경우 검사와 전체 커널 빌드 통과.
- M35H 패키지: xcover5/artifacts/m35h/AP_M35H_NATIVEIOS.tar.md5
- SHA256: db2b6c4e34809ce7061083c0f58a42a332e9dcad1f79b7d56dba1453ef8a330e
- 빠른 init/원본 Apple파일/시험 바이너리 불변, 실제 HFS59항목 소유권·모드 동일, boot-only/OdinMD5/파티션크기 검증 통과.
- 실기기 사진204522에서 M35 JOB PASS 및 m35-proof 종료0 확인. 이번 실행의 시험 작업은 SIGKILL 없이 완료됐으나 긴 지연과 반복 안정성은 미해결이다.

## 20:45 추가 증거: 같은 부팅에서 M35 성공

사진203324 뒤 화면이 유지돼 정체로 판단했으나, 사용자가 계속 실행해 둔 같은 이미지에서 사진204522의 M35 JOB PASS와 종료0이 확인됐다. 영구 정체라는 판단을 철회한다. launchd의 Successfully spawned m35-proof, 자체 proof의 parent PID1 검사, 종료0, launchd EXITED code0이 함께 보인다. KeepAlive=false의 일회성 작업이므로 이후 inactive/not running은 정상 종료 상태다.

초기 부팅 로그00:01:15.357732와 작업 시작00:08:55.079921 사이 게스트 시간 차이는 약7분40초다. 실행 지연과 화면 출력 지연 중 어느 쪽인지 사진만으로 단정할 수 없고, 게스트 시계의 실제 시간 정확도도 별도 검증 대상이다. 이번 성공으로 iOS GUI 부팅이나 반복 안정성을 주장하지 않는다.

정체를 전제로 추가한0045 관측기는 철회했고 진행 중 CI40091257401 취소를 요청했다. M35H를 현재 성공 기준 이미지로 유지하며 새 설치본은 만들지 않는다.

다음 순서: (1) 긴 지연을 실행 대기/파일 페이지인/출력 경로로 나눠 원인을 좁힌다. 소스상 framebuffer 출력에는 명시적 sleep이 없고, eMMC는512바이트 단위 동기PIO이지만 이것만으로7분40초의 원인이라고 확정하지 않는다. (2) 원인에 근거한 성능 변경 후 동일 성공 기준과 소요시간을 비교한다. (3) 최소 bootstrap 등록/조회/요청-응답 및 launchd 반복 안정성 검증으로 진행한다. 그 후 최소 시스템 서비스, 프레임워크, 화면/입력 순서를 따른다.


## M35 성공 이후 지연 조사: 소스 확인 결과

이번 조사에서는 실행 코드를 변경하거나 새 Odin 이미지를 만들지 않았다. M35H의 단일 성공 실행을 기준으로 유지한다.

- framebuffer 송신에는 명시적인 sleep이 없고 transmit_ready는 항상 참이다. 이것은 콘솔의 전체 처리 비용이나 상위 버퍼 지연이 없다는 증거는 아니다.
- eMMC는 512바이트마다 CMD17을 보내는 동기 PIO이며 1초는 매번 기다리는 시간이 아니라 실패 시 제한시간이다. 과거 M17c EXT_CSD 읽기는 6608 ticks/254153ns였다. EXT_CSD 측정으로 런타임 CMD17 처리량을 대체하지 않는다.
- 현재 커널 RAM 창은 256MiB에서 panic용 1MiB를 제외한 약255MiB다. 캐시 전체 크기 약2.72GB와 비교해 cold page-in 비용이 후보지만, 전체 캐시를 한꺼번에 읽는다고 가정하지 않는다. 검증된 물리 메모리 지도를 확인하지 않고 RAM 범위를 늘리지 않는다.
- proof plist는 RunAtLoad=true, KeepAlive=false이며 명시적 지연 키가 없다. 성공 후 service inactive는 정상이다. launchd의 'because speculative' 문구만으로 지연 원인을 확정할 수 없다.

### 다음 구현의 범위와 판단 기준

다음 후보는 성능 개선으로 가장한 타임아웃 축소가 아니라, 성공 경로에 한정한 누적 시간 측정이다. 측정 설계가 구현되기 전에는 새 이미지라고 안내하지 않는다.

1. PID1 Apple launchd 진입, xpcproxy LOAD, m35-proof LOAD 세 지점에서 같은 단조 시계의 시간과 eMMC 누적 섹터 수·읽기 소요시간·오류 수를 기록한다. 섹터마다 로그를 출력하지 않는다.
2. 원시 측정값은 출력 전에 저장한다. 같은 지점에서 콘솔 누적 소요시간도 확보하면 실행과 화면 출력 비용을 비교할 수 있다. 콘솔 안에서 재귀 printf를 호출하지 않는다.
3. 읽기 누적시간이 지연 대부분이면 저장장치 경로를 개선한다. 읽기/콘솔 시간이 작으면 launchd의 타이머·스케줄링·의존 서비스 대기로 조사를 좁힌다. 누적 벽시계 시간은 잠금 대기와 선점을 포함할 수 있으므로 CPU 점유시간으로 해석하지 않는다.
4. 실제 기기에서 M35 JOB PASS, 정상 종료0, 전후 지연 측정이 함께 나와야 개선을 주장한다. 동일 이미지 반복 부팅은 그 다음 안정성 검증으로 한다.

이후 기능 단계는 bootstrap 서비스 등록/조회/요청-응답이다. 현재 성공은 launchd가 단일 자체 작업을 실행한 범위이며 iOS 홈 화면 도달 시점은 아직 산정할 수 없다.


## M35I 시간 측정 구현

0045-xcover5-launch-timing.patch는 launchd.ios / xpcproxy / m35-proof의 LOAD 완료 지점에서 `XCOVER5 PERF LOAD`를 출력한다. ms는 단조 시계의 밀리초, sectors/io_ms/errors는 부팅 후 장치 읽기의 누적값이다. io_ms는 media_lock 획득 이후 CMD17 처리 구간이며 잠금 대기는 제외하고 선점은 포함한다. LOAD는 dyld나 main 진입을 증명하지 않으므로 기존 JOB PASS와 함께 판단한다. 콘솔 출력 비용은 이번 구현에서 별도 계측하지 않는다.

진단은 기존 signing/exec/스토리지 동작을 변경하지 않는다. 섹터별 printf나 새 타이머 스레드는 없다. 원본 사용자 공간 파일, proof와 plist는 그대로 유지한다. 적용 검사와 실제 읽기/스냅샷 함수의 호스트 컴파일 검사를 통과했다. 검사에는 성공, 전송 실패, R1 오류, 범위 밖 요청, 반복 스냅샷, 장치 미준비가 포함된다. 실제 하드웨어 속도 개선을 입증하는 검사는 아니다.

M35I build/package verification: CI40092579110 success, source0d50e212d03fdfa27d548ed7fa9bd84eed0603fc. PERF marker present in actual kernel. AP boot-only/Odin MD5/44MiB partition fit passed. Independent HFS extraction checks passed; all59 catalog entries match M35H. AP SHA256 1f273f6d198c0a633c3d310c1592b643c7c55ed283230ca47633b8451f96ec01. Output: xcover5/artifacts/m35i/AP_M35I_TIMING.tar.md5. Hardware timing result pending; no speedup claim.


## M35I 영상211657: 실기기 성공 및 시간 측정

M34 PASS(exit55), M35 JOB PASS(parentPID1), proof 종료0 확인. launchd.ios LOAD는72549ms/42333sectors/io3795ms/errors0, proof LOAD는78063ms/96701sectors/io8748ms/errors0이다. 두 지점 차이는5.514초이고 전송 누적시간 차이는4.953초(약89.8%)다. 전송 시간은 선점을 포함하므로 CPU 점유율로 해석하지 않는다. xpcproxy 개별 PERF 값은 판독한 프레임에서 확보하지 못했다.

이 실행에서는 early-boot flush→spawn이 약4.436초로, 이전459.7초 지연은 재현되지 않았다. 진단 계측이 타이밍에 영향을 줄 수 있으므로 수정으로 해결됐다고 단정하지 않는다. launchd LOAD 이전72.549초 중 누적 전송시간은3.795초다. 따라서 남은 전체 부팅 시간을 줄이려면 launchd 이전 초기화/대기를 먼저 살펴야 한다. 화면에 오래 남은 ifnet/dlil 메시지 자체가 원인임을 입증하지는 않는다. 분석 프레임·원본 영상·수치는 프로젝트 artifacts/m35i/video-211657에 저장했다. 이번 영상 검토에서는 새 펌웨어를 만들지 않았다.


## M35J: 현재 포트에 없는 RTC 서비스 대기 제거

IOStartIOKit.cpp의 IOKitInitializeTime은 IORTC 서비스를 최대30초 기다린 뒤 clock_initialize_calendar를 실행한다. 현재 보드 포트와 빌드에 IORTC 제공 드라이버가 없다. 0046은 XCOVER5에만 이 서비스 대기를 생략하며 달력 초기화는 유지한다. BCM2837의 기존 예외와 다른 보드/x86의 동작을 유지한다. 향후 RTC 드라이버를 연결할 때 이 예외도 재검토해야 한다.

전체72.549초의 원인이 모두 RTC라는 주장은 하지 않는다. 루트 IOBSD 준비에도 최대30초 대기가 있지만 실제 timeout 증거를 확보하지 못했으므로 변경하지 않았다. dlil/ifnet의 준비 predicate, lock, wakeup을 검사했으며 대기 제거 근거를 찾지 못했다. 오래 남은 영상에는 이 스레드들이 Proceeding에 도달한 메시지도 있다.

패치 적용 검사와 추출한 실제 IOKitInitializeTime 함수의 호스트 검사 통과: XCover5/BCM2837/기타ARM/x86 네 구성에서 기대한 서비스 대기와 달력 초기화 횟수를 확인했다. 호스트의 내장 x86_64 매크로는 시험 함수에서만 TEST_X86_64로 치환해 ARM 분기를 검사했다. 전체 커널 CI40094554593 진행 중.

다음 실기기 판정: RTC skip 메시지, launchd/proof PERF 시간, M34 PASS, M35 JOB PASS와 종료0. M35I launchd72549ms/proof78063ms를 비교 기준으로 삼되 단일 부팅의 차이를 반복 안정성으로 해석하지 않는다. 이후 최소 bootstrap 이름 등록/조회/요청-응답을 구현한다.

M35J verification complete: CI40094554593 SUCCESS (a72a508fcc7b749ae3a94f49e88a4b14dba5b13f). Actual kernel RTC skip/PERF markers verified. Boot-only archive, Odin MD5, partition fit, unchanged probes/init/proof/shim/DTB, independent HFS extraction and accounts PASS. AP: xcover5/artifacts/m35j/AP_M35J_RTC_WAIT.tar.md5; SHA256 d30bd6653b4fe17db9d5be9d91a3b3d52b648eca22dee638370d1fff43211171. Hardware speedup remains pending.


## M35J 영상214720 실기기 결과

M34 PASS(exit55), M35 JOB PASS(parent PID1), proof 종료0 확인. launchd LOAD 42759ms/42333sectors/io3795ms/errors0, proof LOAD 48270ms/96701sectors/io8748ms/errors0. M35I 대비 각각29790ms/29793ms 단축. launchd 이후 구간은5511ms로 이전5514ms와 거의 같고 읽기량·누적전송시간도 동일하다. 이번 부팅은 RTC 대기 제거에 따른 약29.8초 단축을 뒷받침한다. 반복 안정성과 과거 간헐적 지연의 완전 해결은 아직 입증하지 않았다. 다음은 launchd 이름 기반 서비스 등록/조회/요청-응답 검증. 원본과 분석은 artifacts/m35j/video-214720에 저장했다.


## M36: launchd 이름 기반 Mach 서비스 시험

M35의 원본 proof와 PID1 인계는 유지한다. 새 org.xcover5.m36.echo 작업은 MachServices 이름을 선언하고 RunAtLoad=true/KeepAlive=false로 한 번 실행된다. 서버는 부모PID1을 검사하고 task_get_special_port로 얻은 기존 bootstrap에 bootstrap_check_in을 요청한다. 서버가 fork한 별도 클라이언트는 bootstrap_look_up으로 서비스 send right를 얻는다. 기존 M34의 임시 bootstrap 포트 교체 방식은 사용하지 않는다.

요청/응답은 메시지 크기·ID·payload·서로의 PID·send-once 권리를 확인한다. Mach send/receive 각각5000ms timeout; 부모는 WNOHANG으로 자식 exit56을 제한 횟수만 기다리고, 성공 시 수신 포트를 정리한 뒤0으로 종료한다. 실패에는100~127 단계 종료코드가 남고 부모 실패 시 아직 회수하지 않은 자식만 종료한다. bootstrap 라이브러리 호출 자체에는 새 timeout을 추가하지 않는다.

이 시험은 이름 조회와 launchd 제공 포트 사용을 검증한다. 서로 독립적으로 exec된 클라이언트나 on-demand 서비스 재기동, 일반 XPC 객체 메시징, GUI는 아직 검증하지 않는다. 다음 단계는 M36 실제 성공 후 독립 클라이언트 및 재기동 검증이다.

M36 build/package complete: CI40095942062 SUCCESS, source efd687f. ARM64 mocked imports11 cases PASS; independent Mach-O/binding/signature decoder PASS. Independent HFS extraction verifies12 executables including unchanged M35 and original Apple assets; both job plists/account records valid. Boot-only/Odin MD5/44MiB fit and RTC/PERF markers PASS. AP artifacts/m36/AP_M36_BOOTSTRAP.tar.md5 SHA25684ffd5a9b54e63fe53a9a06d8cb464e4b846b99fd190b7d5d85060ed6cc5dc42. Hardware M36 remains pending.


## M36 video220556 hardware failure

Service check-in PASS, but launchd denies the forked client pid7 lookup of org.xcover5.m36.echo with error159 Sandbox restriction. Client exit121; server exit109 after approximately5.011s, consistent with its receive timeout. M36 request/reply is not verified. The root authorization cause remains unknown; next inspect client identity/audit context and lookup policy, then validate lookup and request/reply with real launchd. Do not treat mock import tests as policy coverage. Evidence: artifacts/m36/video-220556/review.txt. No firmware changes in this review.


## M36A scoped bootstrap compatibility

Original launchd 0x1000300fc calls its sandbox wrapper; 0x1000154c0 calls sandbox_check_by_audit_token and considers only zero allowed. iOS16.5 libsystem_sandbox at0x1d0c2eb18 passes PID/pidversion into call2 of policy Sandbox through syscall381. The check core at0x1d0c2ee70 returns -1 on syscall error. Stock mac_base.c returns ENOPOLICY when the policy is absent. This explains how missing policy support produces the observed restriction; hardware confirmation of the new handler remains required.

0047 adds an XCOVER5-only fallback after unsuccessful policy dispatch. Existing registered policy callbacks always retain their results. It accepts only PID1/64-bit caller, call2/Sandbox, exact mach-lookup operation, global-name filter7, audit-version flag0x40000000, exact org.xcover5.m36.echo service, live root m36-probe client with matching pidversion, and m36-probe parent whose parent is PID1. Copies are bounded and checked; other requests remain errors. This bring-up allowlist does not implement general Sandbox security or enable arbitrary services. Host positive/negative checks pass; original userspace/probe remains unchanged.


M36A complete: CI40098125628 SUCCESS, source fd0a3c9. Original ARM64 sandbox-check ABI emulation and host helper/dispatch negative tests PASS. Package marker confirms0047 compiled. Independent HFS comparison:61 paths/modes and35 files unchanged fromM36; volume metadata timestamps/ID differ. Boot33472512bytes, boot-only/OdinMD5/partitionfit PASS. AP artifacts/m36a/AP_M36A_LOOKUP.tar.md5 SHA256ad676168b570ffe81c335785600410d9c4a5268376d4681557da914c40c0711c. Actual hardware pending. This is an exact M36 service bring-up allowlist, not generic Sandbox support. Next: verify M36 CHECKIN, scoped allow, PEER/CHILD PASS, server exit0; only then expand to independent service client/on-demand lifecycle. Evidence research/launchd-rootcause/M36A-analysis.txt.


## M36A video223917: hardware failure persists

M36A hardware review: video223917 (59.84 seconds)
FAIL: M36 CHECKIN PASS, then launchd denied lookup org.xcover5.m36.echo by m36-probe[7], error159 Sandbox restriction.
Evidence frame009 and frame011/012: client pid7 rv7900 => exit121; server pid6 rv6d00 => exit109, also explicitly logged exit(109).
Lookup denial at00:00:49.841437; server exit at00:00:54.843808 (~5.002371s).
No scoped M36A allow marker, PEER PASS or CHILD PASS in these frames. The proposed compatibility fix has not resolved this hardware failure. Absence of the success marker alone does not establish which guard/path rejected the call or prove the flashed image identity.
Next inspect actual syscall dispatch and capture return/guard reason plus runtime build identity before changing the allowlist. Host/emulator tests validated selected inputs only, not actual launchd request and kernel dispatch.
No new firmware created during this review.



## M36B: correct lookup filter variants

M36A hardware still failed159/121/109. Static audit found its filter7-only allowlist rejects launchd ordinary lookup (wrapper type1 -> API2 -> internal6). Original ARM64 emulator also verifies API3->7 and API12->50. Patch0048 handles those exact mach-lookup variants and observed cross-domain filter6, preserving service/client/version/parent restrictions and existing registered-policy decisions. Host positive/negative and dispatch tests pass. Actual hardware fix remains pending. Evidence: research/launchd-rootcause/M36B-analysis.txt. Next gate is peer+server request/reply PASS and server exit0, before any next milestone.

M36B build40099788753 SUCCESS, source b2642dc. Packaged artifacts/m36b/AP_M36B_LOOKUP_FILTERS.tar.md5 SHA25643a18b385651363f97dcf4d88def70374c7accd56ee55ebf7a049fe00059835c. Actual kernel marker, manifest, boot-only archive/MD5/size, unchanged shim/DTB, and independent HFS61paths/35files comparison PASS. Hardware pending; no device write performed.
