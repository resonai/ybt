// Generated by the protocol buffer compiler.  DO NOT EDIT!
// source: app/hello.proto

#ifndef PROTOBUF_app_2fhello_2eproto__INCLUDED
#define PROTOBUF_app_2fhello_2eproto__INCLUDED

#include <string>

#include <google/protobuf/stubs/common.h>

#if GOOGLE_PROTOBUF_VERSION < 2006000
#error This file was generated by a newer version of protoc which is
#error incompatible with your Protocol Buffer headers.  Please update
#error your headers.
#endif
#if 2006001 < GOOGLE_PROTOBUF_MIN_PROTOC_VERSION
#error This file was generated by an older version of protoc which is
#error incompatible with your Protocol Buffer headers.  Please
#error regenerate this file with a newer version of protoc.
#endif

#include <google/protobuf/generated_message_util.h>
#include <google/protobuf/message.h>
#include <google/protobuf/repeated_field.h>
#include <google/protobuf/extension_set.h>
#include <google/protobuf/unknown_field_set.h>
// @@protoc_insertion_point(includes)

namespace tests {

// Internal implementation detail -- do not call these.
void  protobuf_AddDesc_app_2fhello_2eproto();
void protobuf_AssignDesc_app_2fhello_2eproto();
void protobuf_ShutdownFile_app_2fhello_2eproto();

class Hello;

// ===================================================================

class Hello : public ::google::protobuf::Message {
 public:
  Hello();
  virtual ~Hello();

  Hello(const Hello& from);

  inline Hello& operator=(const Hello& from) {
    CopyFrom(from);
    return *this;
  }

  inline const ::google::protobuf::UnknownFieldSet& unknown_fields() const {
    return _unknown_fields_;
  }

  inline ::google::protobuf::UnknownFieldSet* mutable_unknown_fields() {
    return &_unknown_fields_;
  }

  static const ::google::protobuf::Descriptor* descriptor();
  static const Hello& default_instance();

  void Swap(Hello* other);

  // implements Message ----------------------------------------------

  Hello* New() const;
  void CopyFrom(const ::google::protobuf::Message& from);
  void MergeFrom(const ::google::protobuf::Message& from);
  void CopyFrom(const Hello& from);
  void MergeFrom(const Hello& from);
  void Clear();
  bool IsInitialized() const;

  int ByteSize() const;
  bool MergePartialFromCodedStream(
      ::google::protobuf::io::CodedInputStream* input);
  void SerializeWithCachedSizes(
      ::google::protobuf::io::CodedOutputStream* output) const;
  ::google::protobuf::uint8* SerializeWithCachedSizesToArray(::google::protobuf::uint8* output) const;
  int GetCachedSize() const { return _cached_size_; }
  private:
  void SharedCtor();
  void SharedDtor();
  void SetCachedSize(int size) const;
  public:
  ::google::protobuf::Metadata GetMetadata() const;

  // nested types ----------------------------------------------------

  // accessors -------------------------------------------------------

  // optional string world = 1;
  inline bool has_world() const;
  inline void clear_world();
  static const int kWorldFieldNumber = 1;
  inline const ::std::string& world() const;
  inline void set_world(const ::std::string& value);
  inline void set_world(const char* value);
  inline void set_world(const char* value, size_t size);
  inline ::std::string* mutable_world();
  inline ::std::string* release_world();
  inline void set_allocated_world(::std::string* world);

  // @@protoc_insertion_point(class_scope:tests.Hello)
 private:
  inline void set_has_world();
  inline void clear_has_world();

  ::google::protobuf::UnknownFieldSet _unknown_fields_;

  ::google::protobuf::uint32 _has_bits_[1];
  mutable int _cached_size_;
  ::std::string* world_;
  friend void  protobuf_AddDesc_app_2fhello_2eproto();
  friend void protobuf_AssignDesc_app_2fhello_2eproto();
  friend void protobuf_ShutdownFile_app_2fhello_2eproto();

  void InitAsDefaultInstance();
  static Hello* default_instance_;
};
// ===================================================================


// ===================================================================

// Hello

// optional string world = 1;
inline bool Hello::has_world() const {
  return (_has_bits_[0] & 0x00000001u) != 0;
}
inline void Hello::set_has_world() {
  _has_bits_[0] |= 0x00000001u;
}
inline void Hello::clear_has_world() {
  _has_bits_[0] &= ~0x00000001u;
}
inline void Hello::clear_world() {
  if (world_ != &::google::protobuf::internal::GetEmptyStringAlreadyInited()) {
    world_->clear();
  }
  clear_has_world();
}
inline const ::std::string& Hello::world() const {
  // @@protoc_insertion_point(field_get:tests.Hello.world)
  return *world_;
}
inline void Hello::set_world(const ::std::string& value) {
  set_has_world();
  if (world_ == &::google::protobuf::internal::GetEmptyStringAlreadyInited()) {
    world_ = new ::std::string;
  }
  world_->assign(value);
  // @@protoc_insertion_point(field_set:tests.Hello.world)
}
inline void Hello::set_world(const char* value) {
  set_has_world();
  if (world_ == &::google::protobuf::internal::GetEmptyStringAlreadyInited()) {
    world_ = new ::std::string;
  }
  world_->assign(value);
  // @@protoc_insertion_point(field_set_char:tests.Hello.world)
}
inline void Hello::set_world(const char* value, size_t size) {
  set_has_world();
  if (world_ == &::google::protobuf::internal::GetEmptyStringAlreadyInited()) {
    world_ = new ::std::string;
  }
  world_->assign(reinterpret_cast<const char*>(value), size);
  // @@protoc_insertion_point(field_set_pointer:tests.Hello.world)
}
inline ::std::string* Hello::mutable_world() {
  set_has_world();
  if (world_ == &::google::protobuf::internal::GetEmptyStringAlreadyInited()) {
    world_ = new ::std::string;
  }
  // @@protoc_insertion_point(field_mutable:tests.Hello.world)
  return world_;
}
inline ::std::string* Hello::release_world() {
  clear_has_world();
  if (world_ == &::google::protobuf::internal::GetEmptyStringAlreadyInited()) {
    return NULL;
  } else {
    ::std::string* temp = world_;
    world_ = const_cast< ::std::string*>(&::google::protobuf::internal::GetEmptyStringAlreadyInited());
    return temp;
  }
}
inline void Hello::set_allocated_world(::std::string* world) {
  if (world_ != &::google::protobuf::internal::GetEmptyStringAlreadyInited()) {
    delete world_;
  }
  if (world) {
    set_has_world();
    world_ = world;
  } else {
    clear_has_world();
    world_ = const_cast< ::std::string*>(&::google::protobuf::internal::GetEmptyStringAlreadyInited());
  }
  // @@protoc_insertion_point(field_set_allocated:tests.Hello.world)
}


// @@protoc_insertion_point(namespace_scope)

}  // namespace tests

#ifndef SWIG
namespace google {
namespace protobuf {


}  // namespace google
}  // namespace protobuf
#endif  // SWIG

// @@protoc_insertion_point(global_scope)

#endif  // PROTOBUF_app_2fhello_2eproto__INCLUDED
