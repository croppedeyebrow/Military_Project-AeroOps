# Vehicle3DViewer

선택 기체만 Three.js 저폴리곤 GLB로 표현하고 roll·pitch·yaw quaternion을
적용한다. 6단계(`docs/roadmap/06_단계_3D상세뷰어_Day1415.md`)에서 구현.

3D 오류가 2D 지도 관제를 중단시키지 않도록 오류 경계(Error Boundary)를 둔다
(`docs/planning/01_프론트엔드_아키텍처.md`).
