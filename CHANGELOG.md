# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- AEC filter strength tuning option

### Fixed
- Ensure recording continues after batch device switch
- Properly pause reader threads during batch device switch
- Resolve mypy type check errors

## [0.7.2] - 2025-01-XX

### Added
- Handle simultaneous multiple device failures
- CI workflow for lint, typecheck, and test
- Auto-switch to alternative device on disconnection

### Fixed
- Stop recording immediately on device error

## [0.7.1] - 2025-01-XX

### Fixed
- Handle already-closed stream in WasapiStream.close()

## [0.7.0] - 2025-01-XX

### Added
- Device disconnect handling during recording (#3)

### Changed
- Phase 6 timer features documented in roadmap

## [0.6.1] - 2025-01-XX

### Fixed
- Resolve all lint errors (line-too-long and unused imports)

## [0.6.0] - 2025-01-XX

### Added
- Configuration file support (#16)
- Project documentation (CONCEPT, DESIGN, CONTRIBUTING)

## [0.5.0] - 2025-01-XX

### Added
- Device switching documentation
- Keyboard-based device switching during recording (#15)
- GitHub Actions release automation workflow

### Fixed
- Escape bracket characters in keyboard shortcuts display
- Add missing logger definition in record_dual_to_file

## [0.4.2] - 2025-01-XX

### Added
- Portable build documentation to README

### Fixed
- PyInstaller missing rich._unicode_data modules
- Add pyaec binaries to a.binaries instead of Analysis parameter
- Explicitly collect pyaec DLL for portable build
- Use shutil.make_archive return value for correct ZIP path
- Handle invalid binary entries in collect_dynamic_libs
- Add dependency-groups for uv sync --group build

## [0.4.0] - 2025-01-XX

### Added
- PyInstaller portable package build support
- Direct MP3 output for long recordings (--direct-mp3 option)
- --mic-gain and --loopback-gain options
- mix-ratio option for improved mic audio level with AGC tuning

### Changed
- Change default MP3 output to streaming mode
- Default mic_gain from 1.0 to 1.5

### Fixed
- Memory leak with improved resource release handling
- Stabilize AGC by widening window and narrowing gain range
- Add signature sync test for main.start and record.start

## [0.3.0] - 2025-01-XX

### Added
- Software AEC (Acoustic Echo Cancellation) for dual recording
- Automatic gain control for mic/loopback volume matching
- Default to mic+loopback recording (BOTH mode)

### Changed
- pyaec is now a default dependency instead of optional
- Defaults changed to --mix and --aec for dual recording

### Fixed
- Normalize both mic and loopback to target volume level
- Maintain sample synchronization in AEC processing
- Use correct pyaec API (Aec class, cancel_echo method)

## [0.2.1] - 2025-01-XX

### Changed
- Replace Makefile with taskipy for task running

### Fixed
- All lint/type errors

## [0.2.0] - 2025-01-XX

### Added
- MP3 output support (Issue #1)
- Bilingual README support (English/Japanese)

### Changed
- Pin Python version to 3.13 for lameenc compatibility
- lameenc is now a required dependency for MP3 default

### Fixed
- MP3 output path handling when user specifies .mp3 extension
- Loopback echo by using left channel only

## [0.1.0] - 2025-01-XX

### Added
- Phase 2: Simultaneous mic + system audio recording
- Phase 1 MVP for Omni Meeting Recorder
- Windows setup and testing instructions
- Default microphone detection by name matching
- WASAPI loopback support for system audio capture

### Fixed
- Dual recording with parallel thread reading
- Dual recording timing using loopback as master clock
- Block noise in dual recording with synchronous approach
- Audio corruption in dual recording
- Sample rate mismatch in dual recording
- Ctrl+C handling and loopback device detection
- WASAPI loopback stream opening

[Unreleased]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.7.2...HEAD
[0.7.2]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.4.0...v0.4.2
[0.4.0]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/dobachi/omni-meeting-recorder/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dobachi/omni-meeting-recorder/releases/tag/v0.1.0
