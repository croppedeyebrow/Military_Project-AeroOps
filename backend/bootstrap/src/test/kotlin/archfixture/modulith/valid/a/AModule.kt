package archfixture.modulith.valid.a

import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.PackageInfo

/** a는 b에만 의존할 수 있다고 선언했다. */
@PackageInfo
@ApplicationModule(allowedDependencies = ["b"])
class AModule
