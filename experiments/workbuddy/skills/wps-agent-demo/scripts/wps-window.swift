import CoreGraphics
import Foundation
let items = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String:Any]] ?? []
for item in items {
    guard let owner = item[kCGWindowOwnerName as String] as? String,
          owner == "WPS Office", (item[kCGWindowLayer as String] as? Int) == 0,
          let bounds = item[kCGWindowBounds as String] as? [String:Double] else { continue }
    let name = item[kCGWindowName as String] as? String ?? ""
    let result: [String:Any] = ["owner":owner,"title":name,"bounds":bounds]
    let data = try! JSONSerialization.data(withJSONObject:result,options:[.sortedKeys])
    print(String(data:data,encoding:.utf8)!)
}
