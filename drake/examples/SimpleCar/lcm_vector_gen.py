#!/usr/bin/env python

"""Generate c++ and LCM definitions for the LCM Vector concept.
"""

import argparse
import os
import subprocess


def put(fileobj, text, newlines_after=0):
    fileobj.write(text.strip('\n') + '\n' * newlines_after)


INDICES_BEGIN = """
struct %(indices)s {
  static const int kNumCoordiates = %(nfields)d;
"""
INDICES_FIELD = """static const int %(kname)s = %(k)d;"""
INDICES_END = """
};
"""

def to_kname(field):
    return 'k' + ''.join([
        word.capitalize()
        for word in field.split('_')])

def generate_indices(context, fields):
    # pylint: disable=unused-variable
    header = context["header"]
    indices = context["indices"]
    nfields = len(fields)
    put(header, INDICES_BEGIN % locals(), 2)
    for k, field in enumerate(fields):
        kname = to_kname(field)
        put(header, INDICES_FIELD % locals(), 1)
    put(header, INDICES_END % locals(), 2)


DEFAULT_CTOR = """
  %(camel)s() : value_(Eigen::Matrix<ScalarType, K::kNumCoordiates, 1>::Zero()) {}
"""

def generate_default_ctor(context, _):
    header = context["header"]
    put(header, DEFAULT_CTOR % context, 2)


EIGEN_CTOR = """
  template <typename Derived>
  // NOLINTNEXTLINE(runtime/explicit)
  %(camel)s(const Eigen::MatrixBase<Derived>& value)
      : value_(value.segment(0, K::kNumCoordiates)) {}
"""

def generate_eigen_ctor(context, _):
    header = context["header"]
    put(header, EIGEN_CTOR % context, 2)


EIGEN_ASSIGNMENT = """
  template <typename Derived>
  %(camel)s& operator=(const Eigen::MatrixBase<Derived>& value) {
    value_ = value.segment(0, K::kNumCoordiates);
    return *this;
  }
"""


def generate_eigen_assignment(context, _):
    header = context["header"]
    put(header, EIGEN_ASSIGNMENT % context, 2)


TO_EIGEN = """
  friend EigenType toEigen(const %(camel)s<ScalarType>& vec) {
    return vec.value_;
  }
"""


def generate_to_eigen(context, _):
    header = context["header"]
    put(header, TO_EIGEN % context, 2)


COORD_NAMER_BEGIN = """
  friend std::string getCoordinateName(const %(camel)s<ScalarType>& vec,
                                       unsigned int index) {
    switch (index) {
"""
COORD_NAMER_FIELD = """      case K::%(kname)s: return "%(field)s";"""
COORD_NAMER_END = """    }
    throw std::domain_error("unknown coordinate index");
  }
"""


def generate_coord_namer(context, fields):
    # pylint: disable=unused-variable
    header = context["header"]
    indices = context["indices"]
    put(header, COORD_NAMER_BEGIN % context, 1)
    for k, field in enumerate(fields):
        kname = to_kname(field)
        put(header, COORD_NAMER_FIELD % locals(), 1)
    put(header, COORD_NAMER_END % context, 2)


ACCESSOR = """
    const ScalarType& %(field)s() const { return value_(K::%(kname)s); }
    void set_%(field)s(const ScalarType& %(field)s) {
      value_(K::%(kname)s) = %(field)s;
    }
"""

def generate_accessors(context, fields):
    header = context["header"]
    indices = context["indices"]
    # pylint: disable=unused-variable
    for field in fields:
        kname = to_kname(field)
        put(header, ACCESSOR % locals(), 2)


ENCODE_BEGIN = """
template <typename ScalarType>
bool encode(const double& t, const %(camel)s<ScalarType>& wrap,
            // NOLINTNEXTLINE(runtime/references)
            drake::lcmt_%(snake)s_t& msg) {
  msg.timestamp = static_cast<int64_t>(t * 1000);
"""
ENCODE_FIELD = """  msg.%(field)s = wrap.%(field)s();"""
ENCODE_END = """
  return true;
}
"""


def generate_encode(context, fields):
    header = context["header"]
    put(header, ENCODE_BEGIN % context, 1)
    # pylint: disable=unused-variable
    for k, field in enumerate(fields):
        put(header, ENCODE_FIELD % locals(), 1)
    put(header, ENCODE_END % context, 2)


DECODE_BEGIN = """
template <typename ScalarType>
bool decode(const drake::lcmt_%(snake)s_t& msg,
            // NOLINTNEXTLINE(runtime/references)
            double& t,
            // NOLINTNEXTLINE(runtime/references)
            %(camel)s<ScalarType>& wrap) {
  t = static_cast<double>(msg.timestamp) / 1000.0;
"""
DECODE_FIELD = """  wrap.set_%(field)s(msg.%(field)s);"""
DECODE_END = """
  return true;
}
"""


def generate_decode(context, fields):
    header = context["header"]
    put(header, DECODE_BEGIN % context, 1)
    # pylint: disable=unused-variable
    for k, field in enumerate(fields):
        put(header, DECODE_FIELD % locals(), 1)
    put(header, DECODE_END % context, 2)


HEADER_PREAMBLE = """
// Copyright 2016 Robot Locomotion Group @ CSAIL. All rights reserved.
#pragma once

// This file is generated by a script.  Do not edit!
// See %(generator)s.

#include <stdexcept>
#include <string>
#include <Eigen/Core>

#include "lcmtypes/drake/lcmt_%(snake)s_t.hpp"

namespace Drake {
"""

CLASS_BEGIN = """
/// Models the Drake::LCMVector concept.
template <typename ScalarType = double>
class %(camel)s {
 public:
  typedef drake::lcmt_%(snake)s_t LCMMessageType;
  static std::string channel() { return "%(screaming_snake)s"; }

  static const int RowsAtCompileTime = Eigen::Dynamic;
  typedef Eigen::Matrix<ScalarType, RowsAtCompileTime, 1> EigenType;
  size_t size() const { return K::kNumCoordiates; }

"""

CLASS_END = """
 private:
  typedef %(indices)s K;
  EigenType value_;
};
"""

HEADER_POSTAMBLE = """
}  // namespace Drake
"""

LCMTYPE_PREAMBLE = """
// This file is generated by %(generator)s. Do not edit.
package drake;

struct lcmt_%(snake)s_t
{
  int64_t timestamp;

"""

LCMTYPE_POSTAMBLE = """
}
"""


def generate_code(args):
    # pylint: disable=unused-variable
    drake_dist_dir = subprocess.check_output(
        "git rev-parse --show-toplevel".split()).strip()
    generator = os.path.abspath(__file__).replace(
        os.path.join(drake_dist_dir, ''), '')
    title_phrase = args.title.split()
    camel = ''.join([x.capitalize() for x in title_phrase])
    indices = camel + 'Indices'
    snake = '_'.join([x.lower() for x in title_phrase])
    screaming_snake = '_'.join([x.upper() for x in title_phrase])
    header_file = os.path.abspath(
        os.path.join(args.header_dir, "%s.h" % snake))

    header = open(header_file, 'w')
    lcmtype = open(
        os.path.join(args.lcmtype_dir, "lcmt_%s_t.lcm" % snake), 'w')

    put(header, HEADER_PREAMBLE % locals(), 2)
    generate_indices(locals(), args.fields)
    put(header, CLASS_BEGIN % locals(), 2)
    generate_default_ctor(locals(), args.fields)
    generate_eigen_ctor(locals(), args.fields)
    generate_eigen_assignment(locals(), args.fields)
    generate_to_eigen(locals(), args.fields)
    generate_coord_namer(locals(), args.fields)
    generate_accessors(locals(), args.fields)
    put(header, CLASS_END % locals(), 2)
    generate_encode(locals(), args.fields)
    generate_decode(locals(), args.fields)
    put(header, HEADER_POSTAMBLE % locals(), 1)

    put(lcmtype, LCMTYPE_PREAMBLE % locals(), 1)
    for field in args.fields:
        put(lcmtype, "  double %s;" % field, 1)
    put(lcmtype, LCMTYPE_POSTAMBLE % locals(), 1)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--header-dir', help="output directory for header file", default=".")
    parser.add_argument(
        '--lcmtype-dir', help="output directory for lcm file", default=".")
    parser.add_argument(
        '--title', help="title phrase, from which type names will be made")
    parser.add_argument(
        'fields', metavar='FIELD', nargs='+', help="field names for vector")
    args = parser.parse_args()
    generate_code(args)

if __name__ == "__main__":
    main()
