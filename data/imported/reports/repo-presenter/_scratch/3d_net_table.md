### Main

| Class | Description |
|---|---|
| `A3DObject` | The base class of all Aspose.ThreeD objects, all sub classes will support dynamic properties. |
| `AnimationChannel` | AnimationChannel.AnimationChannel creates a new animation channel with no target specified. |
| `AnimationClip` | The Animation clip is a collection of animations. |
| `AnimationNode` | Aspose.3D's supports animation hierarchy, each animation can be composed by several animations and animation's key-frame definition. |
| `ArrayList` | Aspose.3D has its own highly optimized implementation of List{T} for better loading/saving performance Only this interface is exposed for user with IList{T} compatible and similar interfaces. |
| `AssetInfo` | Information of asset. |
| `AxisSystem` | Axis system is an combination of coordinate system, up vector and front vector. |
| `BasicLoadOptions` | Basic load options. |
| `BindPoint` | A BindPoint is usually created on an object's property, some property types contains multiple component fields(like a Vector3 field), will generate channel for each component field and connects the field to one or more keyframe sequence instance(s) through the channels. |
| `Bone` | A bone defines the subset of the geometry's control point, and defined blend weight for each control point. |
| `BooleanOperand` | This class encapsulates the transformed mesh as Boolean operation's operand. |
| `BooleanOperator` | Mesh boolean operations (add/subtract/intersect) between two entities. |
| `Box` | Box. |
| `Camera` | The camera describes the eye point of the viewer looking at the scene. |
| `Circle` | A curve consists of a set of points in the edge of the circle shape. |
| `ColladaSaveOptions` | Save options for Collada format. |
| `CompositeCurve` | A is consisting of several curve segments. |
| `Curve` | The base class of all curve implementations. |
| `CustomObject` | Represents custom object data. |
| `Cylinder` | Parameterized Cylinder. |
| `Deformer` | Base class for and. |
| `Dish` | Parameterized dish. |
| `DracoFormat` | Google Draco format. |
| `DracoSaveOptions` | Save options for Google draco files. |
| `Ellipse` | An Ellipse defines a set of points that form the shape of ellipse. |
| `Entity` | The base class of all entities. |
| `EntityRendererKey` | The key of registered entity renderer. |
| `ExportException` | Export exception. |
| `Extrapolation` | Extrapolation.Type gets or sets the extrapolation mode using the ExtrapolationType enum. |
| `FbxLoadOptions` | Load options for FBX format. |
| `FbxSaveOptions` | Save options for FBX format. |
| `FileFormat` | File format definition. |
| `FileFormatType` | File format type. |
| `FileSystem` | File system encapsulation. |
| `FileSystemFactory` | Factory class for FileSystem. |
| `Frustum` | The base class of Camera and Light. |
| `Geometry` | The base class of all renderable geometric objects (like Mesh, Box, Cylinder and etc.). |
| `GlobalTransform` | Global transform is similar to but it's immutable while it represents the final evaluated transformation. |
| `GltfLoadOptions` | Load options for glTF format. |
| `GltfSaveOptions` | Save options for glTF format. |
| `Group` | Group.Group(name:string) creates a Group with the specified name. |
| `HalfSpace` | represents a infinity space which is split by a plane, this can be used with. |
| `IOConfig` | IO config for serialization/deserialization. |
| `IOExtension` | IOExtension.Write writes the Matrix4 value to the provided BinaryWriter. |
| `ImageRenderOptions` | Image render options. |
| `ImportException` | Import exception. |
| `KeyFrame` | KeyFrame.KeyFrame creates a new empty key frame instance. |
| `KeyframeSequence` | KeyframeSequence.KeyframeSequence creates an empty keyframe sequence with no property name. |
| `LambertMaterial` | Material for lambert shading model. |
| `License` | License management class (not available in FOSS version). |
| `Light` | The light illuminates the scene. |
| `Line` | A polyline is a path defined by a set of points with segments, and connected by edges, which means it can also be a set of connected line segments. |
| `LinearExtrusion` | Linear extrusion takes a 2D shape as input and extends the shape in the 3rd dimension. |
| `LoadOptions` | Base class of load options. |
| `Material` | Material defines the parameters necessary for visual appearance of geometry. |
| `MathUtils` | MathUtils.CalcNormal calculates the normal vector of a polygon defined by an array of Vector3 points. |
| `Mesh` | A mesh is made of many n-sided polygons. |
| `Metered` | Metered license management class (not available in FOSS version). |
| `Microsoft3MFFormat` | File format instance for Microsoft 3MF with 3MF related utilities. |
| `Microsoft3MFSaveOptions` | Save options for the 3MF format (compression and printable-geometry flags). |
| `MorphTargetChannel` | A MorphTargetChannel is used by to organize the target geometries. |
| `MorphTargetDeformer` | MorphTargetDeformer provides per-vertex animation. |
| `Node` | Represents an element in the scene graph. |
| `NurbsCurve` | NURBS curve is a curve represented by NURBS(Non-uniform rational basis spline), A NURBS curve is defined by its control points, a set of weighted control points and a knot vector The w component in co. |
| `NurbsDirection` | A 3D surface has two direction, the U and V, the NurbsDirection defines data for each direction. |
| `NurbsSurface` | is a surface represented by NURBS(Non-uniform rational basis spline), A is defined by two and . |
| `ObjLoadOptions` | Load options for Wavefront OBJ format. |
| `ObjSaveOptions` | Save options for Wavefront OBJ format. |
| `ParseException` | ParseException.ParseException creates a new ParseException with the provided error message. |
| `Patch` | A is a parametric modeling surface, similar to , it's also defined by two , the and . |
| `PatchDirection` | Patch's U and V direction. |
| `PbrMaterial` | Material for physically based rendering based on albedo color/metallic/roughness. |
| `PdfFormat` | Adobe's Portable Document Format. |
| `PdfLoadOptions` | Options for PDF loading. |
| `PdfSaveOptions` | The save options in PDF exporting. |
| `PhongMaterial` | Material for blinn-phong shading model. |
| `Plane` | Parameterized plane. |
| `PlyFormat` | The PLY format. |
| `PlyLoadOptions` | PlyLoadOptions.PlyLoadOptions creates a new instance with default options for loading PLY files. |
| `PlySaveOptions` | PlySaveOptions.PlySaveOptions constructs a new instance with default PLY save settings. |
| `PointCloud` | The point cloud contains no topology information but only the control points and the vertex elements. |
| `PolygonBuilder` | A helper class to build polygon for. |
| `PolygonModifier` | PolygonModifier.Triangulate triangulates all faces of the supplied Mesh into triangles. |
| `Pose` | Pose. |
| `Primitive` | Base class for all primitives. |
| `Profile` | 2D Profile in xy plane. |
| `Property` | Class to hold user-defined properties. |
| `PropertyCollection` | The collection of properties. |
| `Pyramid` | Parameterized pyramid. |
| `RectangularTorus` | Parameterized rectangular torus. |
| `RevolvedAreaSolid` | This class represents a solid model by revolving a cross section provided by a profile about an axis. |
| `RvmFormat` | The RVM Format. |
| `SaveOptions` | Base class of save options. |
| `Scene` | A scene is a top-level object that contains the nodes, geometries, materials, textures, animation, poses, sub-scenes and etc. |
| `SceneObject` | The root class of objects that will be stored inside a scene. |
| `Segment` | A segment in composite curve. |
| `SemanticAttribute` | SemanticAttribute.SemanticAttribute creates a new attribute with the specified vertex field semantic. |
| `Shape` | The shape describes the deformation on a set of control points, which is similar to the cluster deformer in Maya. |
| `Skeleton` | The Skeleton is mainly used by CAD software to help designer to manipulate the transformation of skeletal structure, it's usually useless outside the CAD softwares. |
| `SkinDeformer` | A skin deformer contains multiple bones to work, each bone blends a part of the geometry by control point's weights. |
| `Sphere` | Parameterized sphere. |
| `StlLoadOptions` | Load options for STL format. |
| `StlSaveOptions` | Save options for STL format. |
| `SweptAreaSolid` | A SweptAreaSolid constructs a geometry by sweeping a profile along a directrix. |
| `Texture` | This class defines the texture from an external file. |
| `TextureBase` | Base class for all concrete textures. |
| `TextureSlot` | Texture slot in Material, can be enumerated through material instance. |
| `Torus` | Parameterized torus. |
| `Transform` | A transform contains information that allow access to object's translate/scale/rotation or transform matrix at minimum cost This is used by local transform. |
| `TransformBuilder` | **TransformBuilder** lets developers compose, prepend, or append transformation matrices with a selectable composition order, simplifying complex object placement. |
| `TransformedCurve` | A TransformedCurve gives a curve a placement by using a transformation matrix. |
| `TriMesh` | A TriMesh contains raw data that can be used by GPU directly. |
| `TrialException` | Trial exception. |
| `TrimmedCurve` | A bounded curve that trimmed the basis curve at both ends. |
| `Vertex` | Vertex.ReadVector3(field) reads a 3‑component vector from the specified vertex field, enabling extraction of position data. |
| `VertexDeclaration` | VertexDeclaration.VertexDeclaration creates a new, empty vertex declaration instance. |
| `VertexElement` | Base class of vertex elements A vertex element type is identified by VertexElementType. |
| `VertexElementBinormal` | VertexElementBinormal.VertexElementBinormal() creates a new instance with default mapping and reference modes. |
| `VertexElementDoublesTemplate` | A helper class for defining concrete implementations. |
| `VertexElementEdgeCrease` | Defines the edge crease for specified components. |
| `VertexElementFVector` | A helper class for defining concrete implementations. |
| `VertexElementHole` | Defines if specified polygon is hole. |
| `VertexElementIntsTemplate` | A helper class for defining concrete implementations. |
| `VertexElementMaterial` | Vertex element with material index. |
| `VertexElementNormal` | VertexElementNormal.VertexElementNormal(mappingMode, referenceMode) creates a new VertexElementNormal using the given mapping and reference modes. |
| `VertexElementPolygonGroup` | Defines polygon group for specified components to group related polygons together. |
| `VertexElementSmoothingGroup` | A smoothing group is a group of polygons in a polygon mesh which should appear to form a smooth surface. |
| `VertexElementSpecular` | Defines specular color for specified components. |
| `VertexElementTangent` | VertexElementTangent.Tangents provides a list of Vector4 objects representing per‑vertex tangent data. |
| `VertexElementTemplate` | A helper class for defining concrete implementations. |
| `VertexElementUV` | Vertex element with UV coordinates. |
| `VertexElementUserData` | Defines custom user data for specified components. |
| `VertexElementVertexColor` | Vertex element with vector data (normals, tangents, etc.) /// /// Vertex element with color data. |
| `VertexElementVertexCrease` | Defines the vertex crease for specified components. |
| `VertexElementVisibility` | Defines if specified components is visible. |
| `VertexElementWeight` | Defines blend weight for specified components. |
| `VertexField` | VertexField class lets developers define a vertex field by specifying data type, semantic, index, alias, offset, and size, and provides hashing, equality, and comparison operations. |
| `Watermark` | Watermark utilities enable embedding and extracting text watermarks in 3D files, with optional password protection and permanence. |

#### Interfaces

| Interface | Description |
|---|---|
| `IArrayList` | Aspose.3D has its own highly optimized implementation of List{T} for better loading/saving performance Only this interface is exposed for user with IList{T} compatible and similar interfaces. |
| `IIndexedVertexElement` | VertexElement with indices data. |
| `IMeshConvertible` | Entities that implemented this interface can be converted to mesh. |
| `INamedObject` | Object that has a name. |
| `IOrientable` | Orientable entities shall implement this interface. |

#### Structs

| Struct | Description |
|---|---|
| `BoundingBox` | The axis-aligned bounding box. |
| `BoundingBox2D` | BoundingBox2D.BoundingBox2D initializes a new 2‑D bounding box with the specified minimum and maximum vectors. |
| `EndPoint` | The end point to trim the curve, can be a parameter value or a Cartesian point. |
| `FMatrix4` | FMatrix4.FMatrix4 creates a matrix from 16 float values representing each element. |
| `FVector2` | FVector2.FVector2 creates a 2‑D vector with the given x and y float components. |
| `FVector3` | Represents a 3D vector. |
| `FVector4` | FVector4.FVector4(x:float, y:float, z:float, w:float) creates a 4‑D vector with given x, y, z, w values. |
| `Matrix4` | Matrix4.Matrix4 constructs a 4x4 matrix from the 16 supplied float components. |
| `Quaternion` | A quaternion is usually used to represent a rotation in 3D space. |
| `Rect` | Rect represents a rectangle with position and size, offering a Contains method to test whether a point lies inside it. |
| `RelativeRectangle` | RelativeRectangle.RelativeRectangle creates a rectangle with given left, top, width, height offsets. |
| `Vector2` | Vector2.Vector2 creates a vector with both components set to the given scalar. |
| `Vector3` | The Vector3 class supplies full 3‑D vector mathematics, including dot product, cross product, normalization, and angle calculations between directions. |
| `Vector4` | Vector4.Vector4 creates a vector from a Vector3 and a double w component. |

#### Enumerations

| Enumeration | Description |
|---|---|
| `AlphaSource` | Defines whether the texture contains the alpha channel. |
| `ApertureMode` | Camera aperture modes. |
| `Axis` | Axis. |
| `BoneLinkMode` | A bone's link mode refers to the way in which a bone is connected or linked to its parent bone within a hierarchical structure. |
| `BooleanOperation` | Mesh's Boolean operation. |
| `BoundingBoxExtent` | The extent of the bounding box. |
| `ColladaTransformStyle` | The node's transformation style of node. |
| `ComposeOrder` | The order to compose transform matrix. |
| `CoordinateSystem` | Coordinate system. |
| `CurveDimension` | The dimension of the curves. |
| `DracoCompressionLevel` | Compression level for draco file. |
| `ExtrapolationType` | Extrapolation type. |
| `FileContentType` | File content type. |
| `Interpolation` | The key frame's interpolation type. |
| `LightType` | Light types. |
| `MappingMode` | Mapping mode. |
| `NurbsType` | NURBS types. |
| `PatchDirectionType` | Patch direction's types. |
| `PdfLightingScheme` | LightingScheme specifies the lighting to apply to 3D artwork. |
| `PdfRenderMode` | Render mode specifies the style in which the 3D artwork is rendered. |
| `ProjectionType` | Camera's projection types. |
| `PropertyFlags` | Property flags. |
| `ReferenceMode` | Reference mode. |
| `RotationMode` | The frustum's rotation mode. |
| `RotationOrder` | The order controls which rx ry rz are applied in the transformation matrix. |
| `SkeletonType` | Skeleton type. |
| `SplitMeshPolicy` | Split mesh policy. |
| `StepMode` | StepMode.PREVIOUS_VALUE represents stepping to the previous value in a sequence. |
| `TextureFilter` | Filter options during texture sampling. |
| `TextureMapping` | Texture mapping. |
| `VertexElementType` | Vertex element type. |
| `VertexFieldDataType` | Vertex field's data type. |
| `VertexFieldSemantic` | The semantic of the vertex field. |
| `WeightedMode` | WeightedMode enum describes how vertex weights are applied, supporting None, OutWeight, NextInWeight, and Both. |
| `WrapMode` | Texture's wrap mode. |

