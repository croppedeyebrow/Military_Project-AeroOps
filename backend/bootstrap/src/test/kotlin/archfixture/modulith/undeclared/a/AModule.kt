package archfixture.modulith.undeclared.a

import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.PackageInfo

/** a는 어떤 모듈에도 의존하지 못한다고 선언했다. */
@PackageInfo
@ApplicationModule(allowedDependencies = [])
class AModule
